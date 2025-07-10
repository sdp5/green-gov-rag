from rag.embeddings import get_embedding_model
from rag.vector_store import save_vectorstore
from etl.chunker import chunk_pdf
from etl.utils import clean_text
import os

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
os.makedirs(PROCESSED_DIR, exist_ok=True)

def build_embeddings():
    embedder = get_embedding_model()
    for fname in os.listdir(RAW_DIR):
        if fname.endswith(".pdf"):
            print(f"📄 Processing: {fname}")
            chunks = chunk_pdf(os.path.join(RAW_DIR, fname))
            texts = [clean_text(c) for c in chunks]
            save_vectorstore(texts, embedder, fname.replace('.pdf', ''))

if __name__ == "__main__":
    build_embeddings()
