# airflow/dags/greengovrag_pipeline.py
import json
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import your project modules
from etl import chunker, ingest, loader
from rag import embeddings, rag_chain, vector_store

# --- DAG Default Arguments ---
default_args = {
    "owner": "sundeep",
    "depends_on_past": False,
    "retries": 1,
}

dag = DAG(
    "greengovrag_full_pipeline",
    start_date=datetime(2025, 8, 21),
    schedule_interval=None,  # Or '0 2 * * *' for daily at 2 AM
    default_args=default_args,
    catchup=False,
)

# --- Paths & Config ---
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
CHUNK_DIR = PROCESSED_DIR / "chunks"
EMBED_DIR = PROCESSED_DIR / "embeddings"
VECTOR_STORE_PATH = PROCESSED_DIR / "vector_store" / "faiss.index"
CONFIG_PATH = Path("configs/documents_config.yml")
MODEL_NAME = "amazon/bedrock"  # or HF model


# --- Tasks ---
def task_ingest_docs() -> None:
    docs = loader.load_documents_config(CONFIG_PATH)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ingest.download_documents(docs, RAW_DIR)


def task_parse_docs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for doc_file in RAW_DIR.glob("*"):
        text = ingest.dispatch_parser(str(doc_file))
        out_file = PROCESSED_DIR / (doc_file.stem + ".txt")
        out_file.write_text(text)


def task_chunk_docs() -> None:
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    for txt_file in PROCESSED_DIR.glob("*.txt"):
        text = txt_file.read_text()
        chunks = chunker.chunk_text(text)
        out_file = CHUNK_DIR / (txt_file.stem + "_chunks.json")
        with open(out_file, "w") as f:
            json.dump(chunks, f)


def task_embed_docs() -> None:
    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    for chunk_file in CHUNK_DIR.glob("*_chunks.json"):
        with open(chunk_file) as f:
            chunks = json.load(f)
        embedded = embeddings.embed_chunks(chunks, model_name=MODEL_NAME)
        out_file = EMBED_DIR / (chunk_file.stem + "_embeddings.json")
        with open(out_file, "w") as f:
            json.dump(embedded, f)


def task_build_vector_store() -> None:
    VECTOR_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    store = vector_store.build_vector_store_from_folder(EMBED_DIR)
    vector_store.save_vector_store(store, VECTOR_STORE_PATH)


def task_test_rag() -> None:
    # Example: test RAG with metadata filter
    store = vector_store.load_vector_store(VECTOR_STORE_PATH)
    rag = rag_chain.RAGChain(store, model_name=MODEL_NAME)
    query = "What are the biodiversity offsets in NSW?"
    metadata_filter = {"region": "New South Wales", "topic": "biodiversity"}
    result = rag.run(query, metadata_filters=metadata_filter)
    print("RAG Query Result:\n", result)


# --- Operators ---
ingest_task = PythonOperator(
    task_id="ingest_docs",
    python_callable=task_ingest_docs,
    dag=dag,
)
parse_task = PythonOperator(
    task_id="parse_docs",
    python_callable=task_parse_docs,
    dag=dag,
)
chunk_task = PythonOperator(
    task_id="chunk_docs",
    python_callable=task_chunk_docs,
    dag=dag,
)
embed_task = PythonOperator(
    task_id="embed_docs",
    python_callable=task_embed_docs,
    dag=dag,
)
vector_task = PythonOperator(
    task_id="build_vector_store",
    python_callable=task_build_vector_store,
    dag=dag,
)
test_rag_task = PythonOperator(
    task_id="test_rag_query",
    python_callable=task_test_rag,
    dag=dag,
)

# --- Dependencies ---
ingest_task >> parse_task >> chunk_task >> embed_task >> vector_task >> test_rag_task
