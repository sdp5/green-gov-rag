"""Cloud-aware GreenGovRAG ETL Pipeline for Airflow.

This DAG supports both local filesystem and cloud storage (AWS S3, Azure Blob)
for document processing. Storage backend is configured via DAG parameters and
environment variables.

Features:
- Cloud storage integration (AWS S3, Azure Blob, Local)
- Distributed document processing
- Cloud storage sensors for trigger-based processing (S3 and Azure Blob)
- Automatic retry and error handling
- Metadata tracking in database

Storage Provider Configuration:
- AWS S3: Set STORAGE_PROVIDER=aws and configure AWS credentials
- Azure Blob: Set STORAGE_PROVIDER=azure and configure Azure connection string
- Local: Set STORAGE_PROVIDER=local for local filesystem

Airflow Connections Required:
- AWS: Create 'aws_default' connection with AWS credentials
- Azure: Create 'azure_blob_default' connection with connection string

Trigger Mechanism:
- Upload a 'trigger.json' file to {container}/documents/*/trigger.json
- Sensor DAG will detect it and trigger the main ETL pipeline
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.microsoft.azure.sensors.wasb import WasbBlobSensor

from green_gov_rag.config import settings
from green_gov_rag.etl import ingest
from green_gov_rag.etl.db_writer import (
    save_chunks_from_storage,
    save_document_from_storage_metadata,
    update_document_status,
)
from green_gov_rag.etl.loader import get_document_chunks_from_storage
from green_gov_rag.etl.pipeline import EnhancedETLPipeline
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

logger = logging.getLogger(__name__)

# --- DAG Configuration ---
DEFAULT_ARGS = {
    "owner": "greengovrag",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

# DAG Parameters (can be overridden via Airflow Variables)
STORAGE_PROVIDER = Variable.get("STORAGE_PROVIDER", default_var=settings.cloud_provider)
STORAGE_CONTAINER = Variable.get(
    "STORAGE_CONTAINER", default_var=settings.storage_container
)
ENABLE_AUTO_TAGGING = Variable.get("ENABLE_AUTO_TAGGING", default_var="true") == "true"
CHUNK_SIZE = int(Variable.get("CHUNK_SIZE", default_var="1000"))
CHUNK_OVERLAP = int(Variable.get("CHUNK_OVERLAP", default_var="100"))
EMBEDDING_MODEL = Variable.get(
    "EMBEDDING_MODEL", default_var="sentence-transformers/all-MiniLM-L6-v2"
)

# Paths (for local mode fallback)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "configs" / "documents_config.yml"


def get_dag_config() -> dict[str, Any]:
    """Get DAG configuration from Airflow Variables and settings."""
    return {
        "storage_provider": STORAGE_PROVIDER,
        "storage_container": STORAGE_CONTAINER,
        "use_cloud": STORAGE_PROVIDER != "local",
        "enable_auto_tagging": ENABLE_AUTO_TAGGING,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_model": EMBEDDING_MODEL,
        "config_path": str(CONFIG_PATH),
    }


# --- Task Functions ---
def task_ingest_documents(**context: Any) -> list[str]:
    """Ingest documents from config to cloud or local storage.

    Returns:
        List of document IDs
    """
    config = get_dag_config()
    use_cloud = config["use_cloud"]

    logger.info(f"Ingesting documents with storage: {config['storage_provider']}")

    # Use the new ingest_documents function
    document_ids = ingest.ingest_documents(
        use_cloud=use_cloud,
        config_path=config["config_path"],
    )

    logger.info(f"Ingested {len(document_ids)} documents")

    # Push document IDs to XCom for downstream tasks
    context["ti"].xcom_push(key="document_ids", value=document_ids)

    return document_ids


def task_sync_metadata_to_db(**context: Any) -> None:
    """Sync cloud storage metadata to database.

    This task loads metadata from cloud storage and syncs it to the
    PostgreSQL database for querying and tracking.
    """
    config = get_dag_config()

    if not config["use_cloud"]:
        logger.info("Skipping metadata sync - using local storage")
        return

    # Get document IDs from previous task
    document_ids = context["ti"].xcom_pull(
        task_ids="ingest_documents", key="document_ids"
    )

    if not document_ids:
        logger.warning("No document IDs found to sync")
        return

    storage_adapter = ETLStorageAdapter(provider=config["storage_provider"])

    synced_count = 0
    for doc_id in document_ids:
        try:
            # Load metadata from cloud storage
            metadata = storage_adapter.load_metadata(doc_id)

            # Save to database
            save_document_from_storage_metadata(metadata)
            synced_count += 1

            logger.info(f"Synced metadata for document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to sync metadata for {doc_id}: {e}", exc_info=True)

    logger.info(f"Synced {synced_count}/{len(document_ids)} documents to database")


def task_process_documents(**context: Any) -> None:
    """Process documents: parse, chunk, and auto-tag with metadata."""
    config = get_dag_config()

    # Get document IDs from previous task
    document_ids = context["ti"].xcom_pull(
        task_ids="ingest_documents", key="document_ids"
    )

    if not document_ids:
        logger.warning("No documents to process")
        return

    # Initialize pipeline
    pipeline = EnhancedETLPipeline(
        enable_auto_tagging=config["enable_auto_tagging"],
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
        use_cloud=config["use_cloud"],
    )

    logger.info(
        f"Processing {len(document_ids)} documents with pipeline "
        f"(cloud={config['use_cloud']}, tagging={config['enable_auto_tagging']})"
    )

    # Run pipeline
    chunks = pipeline.run(
        config_path=config["config_path"],
        document_ids=document_ids,
    )

    logger.info(f"Processed {len(chunks)} chunks from {len(document_ids)} documents")

    # Push chunk count to XCom
    context["ti"].xcom_push(key="chunk_count", value=len(chunks))


def task_sync_chunks_to_db(**context: Any) -> None:
    """Sync processed chunks from cloud storage to database."""
    config = get_dag_config()

    if not config["use_cloud"]:
        logger.info("Skipping chunk sync - using local storage")
        return

    # Get document IDs from ingest task
    document_ids = context["ti"].xcom_pull(
        task_ids="ingest_documents", key="document_ids"
    )

    if not document_ids:
        logger.warning("No document IDs found to sync chunks")
        return

    total_chunks = 0
    for doc_id in document_ids:
        try:
            # Update document status to processing
            update_document_status(doc_id, "processing")

            # Load chunks from cloud storage
            chunks = get_document_chunks_from_storage(doc_id)

            if chunks:
                # Save chunks to database
                save_chunks_from_storage(
                    document_id=doc_id,
                    chunks=chunks,
                    embedding_model=config["embedding_model"],
                )

                # Update document status
                update_document_status(
                    doc_id,
                    "completed",
                    chunk_count=len(chunks),
                    embedding_model=config["embedding_model"],
                )

                total_chunks += len(chunks)
                logger.info(f"Synced {len(chunks)} chunks for document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to sync chunks for {doc_id}: {e}", exc_info=True)
            update_document_status(doc_id, "failed", error_message=str(e))

    logger.info(f"Synced {total_chunks} total chunks to database")


def task_build_vector_store(**context: Any) -> None:
    """Build vector store from processed chunks.

    Loads chunks from cloud storage or local filesystem and builds
    embeddings for vector similarity search.
    """
    config = get_dag_config()

    logger.info(f"Building vector store with model: {config['embedding_model']}")

    # Get document IDs
    document_ids = context["ti"].xcom_pull(
        task_ids="ingest_documents", key="document_ids"
    )

    if not document_ids:
        logger.warning("No documents to build vector store")
        return

    # Collect all chunks
    all_chunks = []
    if config["use_cloud"]:
        # Load from cloud storage
        for doc_id in document_ids:
            try:
                chunks = get_document_chunks_from_storage(doc_id)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Failed to load chunks for {doc_id}: {e}")
    else:
        # Load from local filesystem
        chunk_dir = Path("data/chunks")
        for chunk_file in chunk_dir.glob("*_chunks.json"):
            with open(chunk_file, encoding="utf-8") as f:
                chunks = json.load(f)
                all_chunks.extend(chunks)

    logger.info(f"Building vector store from {len(all_chunks)} chunks")

    # Build vector store (implementation depends on your vector store backend)
    from langchain_huggingface import HuggingFaceEmbeddings

    from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

    embeddings = HuggingFaceEmbeddings(model_name=config["embedding_model"])
    vector_store = VectorStoreFactory.create_vector_store(
        embeddings=embeddings,
        store_type=settings.vector_store_type,
    )

    vector_store.build_store(all_chunks)

    # Persist vector store
    if config["use_cloud"]:
        # Upload to cloud storage
        vector_store_path = f"vector_store/{datetime.utcnow().isoformat()}"
        vector_store.persist(path=vector_store_path)
        logger.info(f"Uploaded vector store to cloud: {vector_store_path}")
    else:
        # Save locally
        vector_store.persist(path="data/vector_store/faiss_index")
        logger.info("Saved vector store locally")


def task_validate_pipeline(**context: Any) -> None:
    """Validate the complete pipeline with a test query."""
    config = get_dag_config()

    logger.info("Validating pipeline with test query")

    # Load vector store
    from langchain_huggingface import HuggingFaceEmbeddings

    from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

    embeddings = HuggingFaceEmbeddings(model_name=config["embedding_model"])
    vector_store = VectorStoreFactory.create_vector_store(
        embeddings=embeddings,
        store_type=settings.vector_store_type,
    )

    # Load from appropriate location
    if config["use_cloud"]:
        # Find latest vector store in cloud
        pass  # Implementation depends on storage backend
    else:
        vector_store.load(path="data/vector_store/faiss_index")

    # Test query using vector store directly
    test_query = "What are the key environmental regulations?"
    results = vector_store.similarity_search(test_query, k=3)

    # Format results
    if results:
        result_text = f"Found {len(results)} relevant documents:\n"
        for i, doc in enumerate(results, 1):
            content = (
                doc.page_content[:200]
                if hasattr(doc, "page_content")
                else str(doc)[:200]
            )
            result_text += f"{i}. {content}...\n"
    else:
        result_text = "No documents found"

    logger.info(f"Test query result: {result_text[:200]}...")

    # Push validation result to XCom
    context["ti"].xcom_push(key="validation_result", value=result_text[:500])


# --- DAG Definition ---
with DAG(
    "greengovrag_cloud_pipeline",
    default_args=DEFAULT_ARGS,
    description="Cloud-aware GreenGovRAG ETL Pipeline with distributed processing",
    schedule_interval=None,  # Trigger manually or via sensors
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["greengovrag", "etl", "cloud", "rag"],
    params={
        "storage_provider": STORAGE_PROVIDER,
        "enable_auto_tagging": ENABLE_AUTO_TAGGING,
        "chunk_size": CHUNK_SIZE,
    },
) as dag:
    # Task 1: Ingest documents
    ingest_task = PythonOperator(
        task_id="ingest_documents",
        python_callable=task_ingest_documents,
        provide_context=True,
    )

    # Task 2: Sync metadata to database
    sync_metadata_task = PythonOperator(
        task_id="sync_metadata_to_db",
        python_callable=task_sync_metadata_to_db,
        provide_context=True,
    )

    # Task 3: Process documents (parse, chunk, tag)
    process_task = PythonOperator(
        task_id="process_documents",
        python_callable=task_process_documents,
        provide_context=True,
    )

    # Task 4: Sync chunks to database
    sync_chunks_task = PythonOperator(
        task_id="sync_chunks_to_db",
        python_callable=task_sync_chunks_to_db,
        provide_context=True,
    )

    # Task 5: Build vector store
    vector_store_task = PythonOperator(
        task_id="build_vector_store",
        python_callable=task_build_vector_store,
        provide_context=True,
    )

    # Task 6: Validate pipeline
    validate_task = PythonOperator(
        task_id="validate_pipeline",
        python_callable=task_validate_pipeline,
        provide_context=True,
    )

    # Define task dependencies
    (
        ingest_task
        >> sync_metadata_task
        >> process_task
        >> sync_chunks_task
        >> vector_store_task
        >> validate_task
    )


# --- Cloud Storage Sensor DAGs (Optional) ---
# These DAGs monitor cloud storage for new documents and trigger processing

# AWS S3 Sensor DAG
if STORAGE_PROVIDER == "aws":
    with DAG(
        "greengovrag_s3_sensor",
        default_args=DEFAULT_ARGS,
        description="Monitor S3 for new documents and trigger processing",
        schedule_interval=timedelta(minutes=15),
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["greengovrag", "sensor", "s3", "aws"],
    ) as s3_sensor_dag:
        from airflow.operators.trigger_dagrun import TriggerDagRunOperator

        # S3 sensor to detect new documents
        s3_sensor = S3KeySensor(
            task_id="wait_for_new_documents",
            bucket_name=STORAGE_CONTAINER,
            bucket_key="documents/*/trigger.json",  # Trigger file pattern
            wildcard_match=True,
            aws_conn_id="aws_default",
            timeout=60 * 60,  # 1 hour
            poke_interval=60,  # Check every minute
        )

        # Trigger main pipeline when new documents detected
        trigger_pipeline = TriggerDagRunOperator(
            task_id="trigger_etl_pipeline",
            trigger_dag_id="greengovrag_cloud_pipeline",
            wait_for_completion=False,
            conf={
                "triggered_by": "s3_sensor",
                "storage_provider": "aws",
            },
        )

        s3_sensor >> trigger_pipeline


# Azure Blob Storage Sensor DAG
elif STORAGE_PROVIDER == "azure":
    with DAG(
        "greengovrag_azure_sensor",
        default_args=DEFAULT_ARGS,
        description="Monitor Azure Blob Storage for new documents and trigger processing",
        schedule_interval=timedelta(minutes=15),
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["greengovrag", "sensor", "azure", "blob"],
    ) as azure_sensor_dag:
        from airflow.operators.trigger_dagrun import TriggerDagRunOperator

        # Azure Blob sensor to detect new documents
        azure_sensor = WasbBlobSensor(
            task_id="wait_for_new_documents",
            container_name=STORAGE_CONTAINER,
            blob_name="documents/*/trigger.json",  # Trigger file pattern
            wasb_conn_id="azure_blob_default",
            timeout=60 * 60,  # 1 hour
            poke_interval=60,  # Check every minute
            check_options={"prefix": "documents/"},  # Check with prefix
        )

        # Trigger main pipeline when new documents detected
        trigger_pipeline = TriggerDagRunOperator(
            task_id="trigger_etl_pipeline",
            trigger_dag_id="greengovrag_cloud_pipeline",
            wait_for_completion=False,
            conf={
                "triggered_by": "azure_sensor",
                "storage_provider": "azure",
            },
        )

        azure_sensor >> trigger_pipeline


# --- Setup Instructions ---
"""
AWS S3 Setup:
-------------
1. Create Airflow connection:
   airflow connections add aws_default \\
     --conn-type aws \\
     --conn-login YOUR_ACCESS_KEY_ID \\
     --conn-password YOUR_SECRET_ACCESS_KEY \\
     --conn-extra '{"region_name": "us-east-1"}'

2. Set Airflow variables:
   airflow variables set STORAGE_PROVIDER aws
   airflow variables set STORAGE_CONTAINER your-s3-bucket-name

3. Create S3 bucket:
   aws s3 mb s3://your-s3-bucket-name

4. Trigger processing:
   echo '{"trigger": true}' > trigger.json
   aws s3 cp trigger.json s3://your-bucket/documents/federal/trigger.json

Azure Blob Storage Setup:
--------------------------
1. Create Airflow connection:
   airflow connections add azure_blob_default \\
     --conn-type wasb \\
     --conn-login YOUR_STORAGE_ACCOUNT \\
     --conn-password YOUR_ACCOUNT_KEY \\
     --conn-extra '{"connection_string": "DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"}'

   # OR using SAS token:
   airflow connections add azure_blob_default \\
     --conn-type wasb \\
     --conn-extra '{"sas_token": "YOUR_SAS_TOKEN"}'

2. Set Airflow variables:
   airflow variables set STORAGE_PROVIDER azure
   airflow variables set STORAGE_CONTAINER your-container-name

3. Create Azure container:
   az storage container create \\
     -n your-container-name \\
     --connection-string "YOUR_CONNECTION_STRING"

4. Trigger processing:
   echo '{"trigger": true}' > trigger.json
   az storage blob upload \\
     -f trigger.json \\
     -c your-container-name \\
     -n documents/federal/trigger.json \\
     --connection-string "YOUR_CONNECTION_STRING"

Environment Variables (.env):
------------------------------
# AWS
CLOUD_PROVIDER=aws
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
STORAGE_CONTAINER=greengovrag-documents

# Azure
CLOUD_PROVIDER=azure
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
STORAGE_CONTAINER=greengovrag-documents

Testing the DAG:
----------------
# List DAGs
airflow dags list | grep greengovrag

# Test main pipeline
airflow dags test greengovrag_cloud_pipeline 2025-01-01

# Test sensor (AWS)
airflow dags test greengovrag_s3_sensor 2025-01-01

# Test sensor (Azure)
airflow dags test greengovrag_azure_sensor 2025-01-01

# Trigger manually
airflow dags trigger greengovrag_cloud_pipeline \\
  --conf '{"storage_provider": "aws", "enable_auto_tagging": true}'

Monitoring:
-----------
# View DAG runs
airflow dags list-runs -d greengovrag_cloud_pipeline

# View task logs
airflow tasks logs greengovrag_cloud_pipeline ingest_documents <date>

# Monitor sensor
airflow tasks logs greengovrag_s3_sensor wait_for_new_documents <date>
airflow tasks logs greengovrag_azure_sensor wait_for_new_documents <date>
"""
