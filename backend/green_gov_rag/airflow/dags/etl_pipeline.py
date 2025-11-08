"""GreenGovRAG ETL Pipeline DAG using CLI commands.

This DAG orchestrates the complete ETL pipeline for document processing
by calling greengovrag-cli commands via BashOperator:

Pipeline Flow:
1. Ingest: Download documents from configured sources
2. Parse: Extract text from PDFs using Unstructured.io
3. Chunk: Split documents into semantic chunks
4. Load: Save chunks to PostgreSQL database
5. Index: Build vector store for similarity search
6. Query: Test pipeline with sample query

All steps use the greengovrag-cli commands to ensure consistency
between manual and automated runs.
"""

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

# --- DAG Default Arguments ---
default_args = {
    "owner": "greengovrag",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": datetime.timedelta(minutes=5),
}

# --- DAG Definition ---
with DAG(
    dag_id="greengovrag_full_pipeline",
    default_args=default_args,
    description="Complete ETL pipeline using greengovrag-cli commands",
    schedule_interval=None,  # Manual trigger or '0 2 * * *' for daily at 2 AM
    start_date=datetime(2025, 11, 1),
    catchup=False,
    tags=["greengovrag", "etl", "rag"],
) as dag:

    # Task 1: Ingest documents from config
    ingest_task = BashOperator(
        task_id="ingest_documents",
        bash_command="greengovrag-cli etl ingest --config configs/documents_config.yml",
        cwd="/home/sundeep/github/green-gov-rag/backend",
    )

    # Task 2: Parse documents (PDF/HTML to text)
    parse_task = BashOperator(
        task_id="parse_documents",
        bash_command="greengovrag-cli etl parse --input data/raw --output data/processed",
        cwd="/home/sundeep/github/green-gov-rag/backend",
    )

    # Task 3: Chunk documents
    chunk_task = BashOperator(
        task_id="chunk_documents",
        bash_command=(
            "greengovrag-cli etl chunk "
            "--input data/processed "
            "--output data/chunks "
            "--chunk-size 1000 "
            "--chunk-overlap 100"
        ),
        cwd="/home/sundeep/github/green-gov-rag/backend",
    )

    # Task 4: Load chunks to database
    load_db_task = BashOperator(
        task_id="load_chunks_to_db",
        bash_command="greengovrag-cli db load-chunks --chunks-dir data/chunks --batch-size 100",
        cwd="/home/sundeep/github/green-gov-rag/backend",
    )

    # Task 5: Build vector store index
    index_task = BashOperator(
        task_id="build_vector_index",
        bash_command=(
            "greengovrag-cli rag index "
            "--chunks data/chunks "
            "--vector-store faiss "
            "--collection greengovrag"
        ),
        cwd="/home/sundeep/github/green-gov-rag/backend",
    )

    # Task 6: Test query
    test_query_task = BashOperator(
        task_id="test_rag_query",
        bash_command=(
            'greengovrag-cli rag query '
            '"What are the key environmental regulations in Australia?" '
            '--top-k 3'
        ),
        cwd="/home/sundeep/github/green-gov-rag/backend",
    )

    # Define task dependencies
    (
        ingest_task
        >> parse_task
        >> chunk_task
        >> load_db_task
        >> index_task
        >> test_query_task
    )
