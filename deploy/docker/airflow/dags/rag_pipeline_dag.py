"""GreenGovRAG ETL Pipeline DAG for Docker deployment.

This DAG uses greengovrag-cli commands to orchestrate the complete ETL pipeline.
Designed to run in Docker environment with all dependencies installed.

Pipeline Flow:
1. Ingest: Download documents from configured sources
2. Parse: Extract text from PDFs using Unstructured.io
3. Chunk: Split documents into semantic chunks
4. Load: Save chunks to PostgreSQL database
5. Index: Build vector store for similarity search
6. Query: Test pipeline with sample query
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'greengovrag',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='greengovrag_etl_pipeline',
    default_args=default_args,
    description='Complete ETL pipeline using greengovrag-cli commands',
    start_date=datetime(2025, 11, 1),
    schedule_interval='@daily',  # Run daily at midnight
    catchup=False,
    tags=['greengovrag', 'etl', 'docker'],
) as dag:

    # Task 1: Ingest documents from config
    ingest_task = BashOperator(
        task_id='ingest_documents',
        bash_command='greengovrag-cli etl ingest --config /app/configs/documents_config.yml',
    )

    # Task 2: Parse documents (PDF/HTML to text)
    parse_task = BashOperator(
        task_id='parse_documents',
        bash_command='greengovrag-cli etl parse --input /app/data/raw --output /app/data/processed',
    )

    # Task 3: Chunk documents
    chunk_task = BashOperator(
        task_id='chunk_documents',
        bash_command=(
            'greengovrag-cli etl chunk '
            '--input /app/data/processed '
            '--output /app/data/chunks '
            '--chunk-size 1000 '
            '--chunk-overlap 100'
        ),
    )

    # Task 4: Load chunks to database
    load_db_task = BashOperator(
        task_id='load_chunks_to_db',
        bash_command='greengovrag-cli db load-chunks --chunks-dir /app/data/chunks --batch-size 100',
    )

    # Task 5: Build vector store index
    index_task = BashOperator(
        task_id='build_vector_index',
        bash_command=(
            'greengovrag-cli rag index '
            '--chunks /app/data/chunks '
            '--vector-store qdrant '
            '--collection greengovrag'
        ),
    )

    # Task 6: Test query
    test_query_task = BashOperator(
        task_id='test_rag_query',
        bash_command=(
            'greengovrag-cli rag query '
            '"What are the key environmental regulations in Australia?" '
            '--top-k 3'
        ),
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
