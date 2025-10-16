import os
from pathlib import Path

from green_gov_rag.config import settings
from green_gov_rag.etl.chunker import TextChunker
from green_gov_rag.etl.parser import DocumentParser
from green_gov_rag.etl.utils import clean_text
from green_gov_rag.rag.embeddings import ChunkEmbedder
from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

# Use settings for paths
RAW_DIR = Path(settings.local_storage_path) / "raw"
PROCESSED_DIR = Path(settings.local_storage_path) / "processed"
os.makedirs(PROCESSED_DIR, exist_ok=True)


def build_embeddings() -> None:
    """Build vector embeddings from documents in RAW_DIR."""
    embedder = ChunkEmbedder(provider="huggingface")
    chunker = TextChunker()
    parser = DocumentParser()

    # Initialize vector store using factory (automatically uses settings.vector_store_type)
    vector_store = VectorStoreFactory.create_vector_store(
        embeddings=embedder.embedder,
        index_path=os.path.join(
            PROCESSED_DIR, "faiss_index"
        ),  # Used for FAISS fallback
    )

    all_chunks = []

    for fname in os.listdir(RAW_DIR):
        if fname.endswith(".pdf"):
            print(f"📄 Processing: {fname}")
            doc_path = os.path.join(RAW_DIR, fname)

            # Parse document
            doc_text = parser.parse_pdf(doc_path)

            # Clean and chunk
            cleaned = clean_text(doc_text)
            text_chunks = chunker.chunk_text(cleaned)

            # Create chunk dicts with metadata
            chunks = [
                {"content": chunk, "metadata": {"source": fname, "page": i}}
                for i, chunk in enumerate(text_chunks)
            ]
            all_chunks.extend(chunks)

    # Build vector store with all chunks
    if all_chunks:
        vector_store.build_store(all_chunks)
        vector_store.persist()
        print(f"✅ Built vector store with {len(all_chunks)} chunks")


if __name__ == "__main__":
    build_embeddings()
