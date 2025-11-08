"""Cloud-aware GreenGovRAG ETL Pipeline for Airflow using CLI commands.

This DAG supports both local filesystem and cloud storage (AWS S3, Azure Blob)
for document processing using greengovrag-cli commands.

Pipeline Flow (Cloud-aware):
1. Ingest: Download documents to cloud or local storage
2. Pipeline: Run full ETL (parse, chunk, tag) - supports cloud storage
3. Load DB: Sync chunks to PostgreSQL database
4. Index: Build vector store for similarity search
5. Query: Test pipeline with sample query

Storage Provider Configuration:
- Set CLOUD_PROVIDER environment variable: local, aws, or azure
- AWS S3: Configure AWS credentials via environment
- Azure Blob: Configure Azure connection string via environment
- Local: Uses local filesystem (data/raw, data/processed, data/chunks)

All processing is done via greengovrag-cli commands which handle cloud
storage automatically based on configuration.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.microsoft.azure.sensors.wasb import WasbBlobSensor

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
STORAGE_PROVIDER = Variable.get("STORAGE_PROVIDER", default_var="local")
STORAGE_CONTAINER = Variable.get(
    "STORAGE_CONTAINER", default_var="greengovrag-documents"
)
ENABLE_AUTO_TAGGING = Variable.get("ENABLE_AUTO_TAGGING", default_var="true")
WORKING_DIR = Variable.get(
    "WORKING_DIR", default_var="/home/sundeep/github/green-gov-rag/backend"
)


# Build tagging flag for CLI commands
TAGGING_FLAG = "--tag" if ENABLE_AUTO_TAGGING == "true" else "--no-tag"


# --- Main Cloud-Aware Pipeline DAG ---
with DAG(
    dag_id="greengovrag_cloud_pipeline",
    default_args=DEFAULT_ARGS,
    description="Cloud-aware ETL pipeline using greengovrag-cli commands",
    schedule_interval=None,  # Trigger manually or via sensors
    start_date=datetime(2025, 11, 1),
    catchup=False,
    tags=["greengovrag", "etl", "cloud", "rag"],
    params={
        "storage_provider": STORAGE_PROVIDER,
        "enable_auto_tagging": ENABLE_AUTO_TAGGING,
    },
) as dag:
    # Task 1: Ingest documents (cloud-aware via environment config)
    ingest_task = BashOperator(
        task_id="ingest_documents",
        bash_command="greengovrag-cli etl ingest --config configs/documents_config.yml",
        cwd=WORKING_DIR,
        env={"CLOUD_PROVIDER": STORAGE_PROVIDER},
    )

    # Task 2: Run full ETL pipeline (parse, chunk, tag)
    pipeline_task = BashOperator(
        task_id="run_etl_pipeline",
        bash_command=f"greengovrag-cli etl pipeline --config configs/etl_config.yml {TAGGING_FLAG}",
        cwd=WORKING_DIR,
        env={"CLOUD_PROVIDER": STORAGE_PROVIDER},
    )

    # Task 3: Load chunks to database
    load_db_task = BashOperator(
        task_id="load_chunks_to_db",
        bash_command="greengovrag-cli db load-chunks --chunks-dir data/chunks --batch-size 100",
        cwd=WORKING_DIR,
    )

    # Task 4: Build vector store
    index_task = BashOperator(
        task_id="build_vector_index",
        bash_command=(
            "greengovrag-cli rag index "
            "--chunks data/chunks "
            "--vector-store qdrant "
            "--collection greengovrag"
        ),
        cwd=WORKING_DIR,
    )

    # Task 5: Test query
    test_query_task = BashOperator(
        task_id="test_rag_query",
        bash_command=(
            "greengovrag-cli rag query "
            '"What are the key environmental regulations in Australia?" '
            "--top-k 3"
        ),
        cwd=WORKING_DIR,
    )

    # Define task dependencies
    ingest_task >> pipeline_task >> load_db_task >> index_task >> test_query_task


# --- Cloud Storage Sensor DAGs ---
# These DAGs monitor cloud storage for new documents and trigger processing

# AWS S3 Sensor DAG
if STORAGE_PROVIDER == "aws":
    with DAG(
        dag_id="greengovrag_s3_sensor",
        default_args=DEFAULT_ARGS,
        description="Monitor S3 for new documents and trigger processing",
        schedule_interval=timedelta(minutes=15),
        start_date=datetime(2025, 11, 1),
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
        dag_id="greengovrag_azure_sensor",
        default_args=DEFAULT_ARGS,
        description="Monitor Azure Blob Storage for new documents and trigger processing",
        schedule_interval=timedelta(minutes=15),
        start_date=datetime(2025, 11, 1),
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
1. Set Airflow variables:
   airflow variables set STORAGE_PROVIDER aws
   airflow variables set STORAGE_CONTAINER your-s3-bucket-name
   airflow variables set WORKING_DIR /path/to/green-gov-rag/backend

2. Set environment variables in .env:
   CLOUD_PROVIDER=aws
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   AWS_REGION=us-east-1
   STORAGE_CONTAINER=your-bucket-name

3. Create Airflow connection for sensors (optional):
   airflow connections add aws_default \\
     --conn-type aws \\
     --conn-login YOUR_ACCESS_KEY_ID \\
     --conn-password YOUR_SECRET_ACCESS_KEY \\
     --conn-extra '{"region_name": "us-east-1"}'

4. Trigger processing manually:
   airflow dags trigger greengovrag_cloud_pipeline

   Or upload trigger.json to S3:
   echo '{"trigger": true}' > trigger.json
   aws s3 cp trigger.json s3://your-bucket/documents/federal/trigger.json

Azure Blob Storage Setup:
--------------------------
1. Set Airflow variables:
   airflow variables set STORAGE_PROVIDER azure
   airflow variables set STORAGE_CONTAINER your-container-name
   airflow variables set WORKING_DIR /path/to/green-gov-rag/backend

2. Set environment variables in .env:
   CLOUD_PROVIDER=azure
   AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
   STORAGE_CONTAINER=your-container-name

3. Create Airflow connection for sensors (optional):
   airflow connections add azure_blob_default \\
     --conn-type wasb \\
     --conn-extra '{"connection_string": "YOUR_CONNECTION_STRING"}'

4. Trigger processing manually:
   airflow dags trigger greengovrag_cloud_pipeline

   Or upload trigger.json to Azure:
   echo '{"trigger": true}' > trigger.json
   az storage blob upload \\
     -f trigger.json \\
     -c your-container-name \\
     -n documents/federal/trigger.json \\
     --connection-string "YOUR_CONNECTION_STRING"

Testing the DAG:
----------------
# List DAGs
airflow dags list | grep greengovrag

# Test main pipeline
airflow dags test greengovrag_cloud_pipeline 2025-11-01

# Trigger manually
airflow dags trigger greengovrag_cloud_pipeline

# Monitor execution
airflow dags list-runs -d greengovrag_cloud_pipeline

# View task logs
airflow tasks logs greengovrag_cloud_pipeline ingest_documents <execution-date>
"""
