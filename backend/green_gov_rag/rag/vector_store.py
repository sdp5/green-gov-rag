# rag/vector_store.py

"""Vector Store for GreenGovRAG.

LEGACY: This class is maintained for backward compatibility.
New code should use VectorStoreFactory.create_vector_store()

Handles storing, retrieving, and filtering document embeddings for RAG.

1. Supports multiple backends: FAISS, Qdrant, ChromaDB
2. Metadata filtering support: Use metadata_filters in similarity_search.
3. Stores metadata alongside embeddings.
4. Persistent storage: index + metadata saved to disk/database.
5. Supports additions and searches.
6. Easy to integrate into your RAG chain.
"""

from __future__ import annotations

import logging

from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

from .filters import filter_by_metadata

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, embeddings: Embeddings, index_path: str | None = None):
        """Initialize the vector store.

        LEGACY: This class defaults to FAISS for backward compatibility.
        New code should use VectorStoreFactory.create_vector_store()

        :param embeddings: LangChain Embeddings instance (OpenAI/HuggingFace/Bedrock)
        :param index_path: Optional path to persisted FAISS index.
        """
        logger.debug(
            "Using legacy VectorStore class (FAISS only). "
            "For multi-store support, use VectorStoreFactory.create_vector_store(). "
            "See docs/VECTOR_STORE_MIGRATION.md for details."
        )

        self.embeddings = embeddings
        self.store: FAISS | None
        if index_path:
            self.store = FAISS.load_local(
                folder_path=index_path,
                embeddings=embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            self.store = None
        self.index_path = index_path

    def add_documents(self, docs: list[Document]) -> None:
        """Add documents to the vector store.
        :param docs: List of LangChain Document objects.
        """
        if self.store is None:
            msg = "Vector store not initialized. Call build_store first."
            raise ValueError(msg)
        self.store.add_documents(docs)
        if self.index_path:
            self.store.save_local(self.index_path)

    def build_store(self, chunks: list[dict]) -> None:
        """Build vector store from list of chunks.
        Each chunk should be:
        {"content": str, "metadata": dict}.
        """
        documents = [
            Document(page_content=chunk["content"], metadata=chunk.get("metadata", {}))
            for chunk in chunks
        ]
        self.store = FAISS.from_documents(documents, self.embeddings)

    def add_chunks(self, chunks: list[dict]) -> None:
        """Add more chunks to existing store."""
        if self.store is None:
            self.build_store(chunks)
        else:
            documents = [
                Document(
                    page_content=chunk["content"],
                    metadata=chunk.get("metadata", {}),
                )
                for chunk in chunks
            ]
            self.store.add_documents(documents)

    def list_metadata(self):
        """Return a list of metadata dictionaries for all stored embeddings.

        Note: FAISS stores only vectors and doesn't maintain document metadata directly.
        To get all metadata, you need to maintain a separate metadata store or use
        a vector database that supports metadata retrieval (like Qdrant, Chroma, etc.)

        Returns:
            list: Empty list for FAISS backend. Use a different vector store for metadata listing.
        """
        if self.store is None:
            return []

        # FAISS limitation: no built-in metadata iteration
        # Alternative approaches:
        # 1. Use Qdrant/Chroma if metadata listing is required
        # 2. Maintain separate metadata database/file
        # 3. Store metadata externally and sync with vector IDs
        return []

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        metadata_filters: dict | None = None,
    ) -> list[Document]:
        """Perform similarity search with optional metadata filtering.
        :param query: Query string
        :param k: Number of top documents to return
        :param metadata_filters: Dictionary of metadata to filter on
        :return: List of LangChain Document objects.
        """
        if self.store is None:
            msg = "Vector store not initialized."
            raise ValueError(msg)

        # Perform initial similarity search
        results = self.store.similarity_search(query, k=k, filters=metadata_filters)

        # If filters provided, apply them
        if metadata_filters:
            # Convert Document objects to dicts for filtering
            docs_with_meta = [
                {"content": doc.page_content, "metadata": doc.metadata}
                for doc in results
            ]
            filtered_docs_dict = filter_by_metadata(docs_with_meta, metadata_filters)

            # Convert back to Document objects
            results = [
                Document(page_content=d["content"], metadata=d["metadata"])
                for d in filtered_docs_dict
            ]

        return results

    def persist(self, path: str | None = None) -> None:
        """Persist FAISS index locally."""
        if self.store is None:
            msg = "Vector store not initialized. Nothing to persist."
            raise ValueError(msg)
        save_path = path or self.index_path
        if save_path:
            self.store.save_local(save_path)

    def load(self, path: str) -> None:
        self.store = FAISS.load_local(path, self.embeddings)


if __name__ == "__main__":
    # Quick demo
    # from rag.embeddings import ChunkEmbedder
    # from etl.chunker import TextChunker
    #
    # sample_texts = ["LangChain simplifies building AI applications."]
    # text_chunker = TextChunker(chunk_size=512, chunk_overlap=50)
    # chunks = []
    # for text in sample_texts:
    #     chunks.extend([{"content": c, "metadata": {"source": "demo"}} for c in text_chunker.chunk_text(text)])
    #
    # embedder = ChunkEmbedder(provider="huggingface")
    # embedded = embedder.embed_chunks(chunks)
    #
    # store = FAISS.from_documents(
    #     [doc["content"] for doc in embedded],
    #     embedder.embedder,  # your HuggingFace or Bedrock embedding function
    #     metadatas=[doc["metadata"] for doc in embedded]
    # )
    # store.add_documents(embedded)
    #
    # # Search with the first embedding
    # results = store.search(embedded[0]["embedding"], top_k=3)
    # print("Search results:", results)

    from green_gov_rag.rag.embeddings import ChunkEmbedder  # your embeddings wrapper

    # sample chunks
    chunks = [
        {
            "content": "This is a test document about SA native vegetation.",
            "metadata": {"region": "SA", "topic": "vegetation"},
        },
        {
            "content": "NSW requires biodiversity offsets for land clearing.",
            "metadata": {"region": "NSW", "topic": "biodiversity"},
        },
    ]

    embeddings = (
        ChunkEmbedder().embedder
    )  # Initialize your embeddings provider (HuggingFace, Bedrock, etc.)
    store = VectorStore(embeddings=embeddings)
    store.build_store(chunks)

    # Retrieve chunks with optional metadata filtering
    results = store.similarity_search(
        query="What are vegetation clearance rules in SA?",
        k=3,
        metadata_filters={"region": "SA"},
    )

    for r in results:
        print(r.page_content, r.metadata)
