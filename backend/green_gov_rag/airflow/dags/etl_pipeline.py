# airflow/dags/greengovrag_pipeline.py
import json
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import your project modules
from green_gov_rag.etl import ingest, loader
from green_gov_rag.etl.chunker import TextChunker
from green_gov_rag.etl.parsers import get_parser
from green_gov_rag.rag.embeddings import ChunkEmbedder
from green_gov_rag.rag.rag_chain import RAGChain
from green_gov_rag.rag.vector_store import VectorStore

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
CHUNK_DIR = Path("data/chunks")
VECTOR_STORE_DIR = Path("data/vector_store")
CONFIG_PATH = "configs/documents_config.yml"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# --- Tasks ---
def task_ingest_docs() -> None:
    """Download documents from config."""
    docs = loader.load_documents_config(CONFIG_PATH)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ingest.download_documents(docs, str(RAW_DIR))


def task_parse_docs() -> None:
    """Parse downloaded documents to text."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for doc_file in RAW_DIR.rglob("*"):
        if doc_file.is_file() and doc_file.suffix in [".pdf", ".html", ".htm"]:
            parser = get_parser(str(doc_file))
            text = parser(str(doc_file))
            out_file = PROCESSED_DIR / (doc_file.stem + ".txt")
            out_file.write_text(text, encoding="utf-8")


def task_chunk_docs() -> None:
    """Chunk parsed text files."""
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    chunker = TextChunker(chunk_size=1000, chunk_overlap=100)

    for txt_file in PROCESSED_DIR.rglob("*.txt"):
        text = txt_file.read_text(encoding="utf-8")
        chunks = chunker.chunk_text(text)
        out_file = CHUNK_DIR / (txt_file.stem + "_chunks.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2)


def task_build_vector_store() -> None:
    """Embed chunks and build vector store."""
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all chunks
    all_chunks = []
    for chunk_file in CHUNK_DIR.glob("*_chunks.json"):
        with open(chunk_file, encoding="utf-8") as f:
            chunks = json.load(f)
            all_chunks.extend(chunks)

    # Embed and build vector store
    embedder = ChunkEmbedder(model_name=MODEL_NAME)
    embedded_chunks = embedder.embed_chunks(all_chunks)

    # Create embeddings instance for VectorStore
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)

    vector_store = VectorStore(embeddings=embeddings)
    vector_store.build_store(embedded_chunks)
    if vector_store.store:
        vector_store.store.save_local(str(VECTOR_STORE_DIR / "faiss_index"))


def task_test_rag() -> None:
    """Test RAG with sample query."""
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)

    vector_store = VectorStore(
        embeddings=embeddings, index_path=str(VECTOR_STORE_DIR / "faiss_index")
    )

    rag_chain = RAGChain(vector_store)
    query = "What are the biodiversity offsets in NSW?"
    result = rag_chain.query(query)
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
ingest_task >> parse_task >> chunk_task >> vector_task >> test_rag_task
