from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from green_gov_rag.scripts import build_embeddings, download_docs, evaluate_model

default_args = {
    'owner': 'greengovrag',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
        dag_id='green_gov_rag_etl',
        default_args=default_args,
        start_date=datetime(2025, 7, 10),
        schedule_interval='@daily',
        catchup=False
) as dag:

    t1 = PythonOperator(
        task_id='download_documents',
        python_callable=download_docs.main,
    )

    t2 = PythonOperator(
        task_id='build_embeddings',
        python_callable=build_embeddings.build_embeddings,
    )

    t3 = PythonOperator(
        task_id='evaluate_queries',
        python_callable=evaluate_model.evaluate,
    )

    t1 >> t2 >> t3
