"""FAISS vector store implementation."""

from __future__ import annotations

import logging
from typing import Any

from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

from green_gov_rag.rag.filters import filter_by_metadata
from green_gov_rag.rag.vector_store_interface import VectorStoreInterface

logger = logging.getLogger(__name__)


class FAISSVectorStore(VectorStoreInterface):
    """FAISS-based vector store implementation.

    Fast, in-memory vector similarity search.
    Best for: Development, small datasets, single-server deployments
    """

    def __init__(
        self,
        embeddings: Embeddings,
        index_path: str | None = None,
        **kwargs: Any,
    ):
        """Initialize FAISS vector store.

        Args:
            embeddings: Embeddings model
            index_path: Path to persisted FAISS index
            **kwargs: Additional arguments (ignored)
        """
        super().__init__(embeddings)
        self.index_path = index_path
        self.store: FAISS | None = None

        if index_path:
            try:
                self.load(index_path)
                logger.info(f"Loaded FAISS index from {index_path}")
            except Exception as e:
                logger.warning(f"Could not load FAISS index: {e}")
                self.store = None

    def add_documents(self, docs: list[Document]) -> None:
        """Add documents to the vector store."""
        if self.store is None:
            raise ValueError("Vector store not initialized. Call build_store first.")

        self.store.add_documents(docs)

        if self.index_path:
            self.persist()

    def build_store(self, chunks: list[dict], batch_size: int = 100) -> None:
        """Build vector store from chunks using batched processing.

        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of documents to process per batch (default: 100)
        """
        if not chunks:
            logger.warning("No chunks provided for indexing")
            return

        total_batches = (len(chunks) + batch_size - 1) // batch_size
        logger.info(
            f"Building FAISS store with {len(chunks)} chunks in {total_batches} batches"
        )

        # Process first batch to create index
        first_batch_size = min(batch_size, len(chunks))
        first_batch = chunks[:first_batch_size]
        documents = [
            Document(page_content=chunk["content"], metadata=chunk.get("metadata", {}))
            for chunk in first_batch
        ]

        self.store = FAISS.from_documents(documents, self.embeddings)
        logger.info(
            f"Created FAISS index with first batch of {len(first_batch)} chunks"
        )

        # Process remaining batches if any
        if len(chunks) > first_batch_size:
            for i in range(first_batch_size, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                batch_num = (i // batch_size) + 1

                documents = [
                    Document(
                        page_content=chunk["content"],
                        metadata=chunk.get("metadata", {}),
                    )
                    for chunk in batch
                ]

                self.add_documents(documents)
                logger.info(
                    f"Added batch {batch_num}/{total_batches}: {len(documents)} chunks"
                )

        logger.info(f"Completed building FAISS store with {len(chunks)} total chunks")

    def add_chunks(self, chunks: list[dict]) -> None:
        """Add chunks to existing store."""
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
            self.add_documents(documents)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        metadata_filters: dict | None = None,
    ) -> list[Document]:
        """Perform similarity search with optional metadata filtering."""
        if self.store is None:
            raise ValueError("Vector store not initialized.")

        # FAISS doesn't support native metadata filtering
        # Retrieve more results and filter manually
        fetch_k = k * 3 if metadata_filters else k
        results = self.store.similarity_search(query, k=fetch_k)

        # Apply metadata filters
        if metadata_filters:
            docs_with_meta = [
                {"content": doc.page_content, "metadata": doc.metadata}
                for doc in results
            ]
            filtered_docs_dict = filter_by_metadata(docs_with_meta, metadata_filters)

            results = [
                Document(page_content=d["content"], metadata=d["metadata"])
                for d in filtered_docs_dict[:k]
            ]

        return results[:k]

    def persist(self, path: str | None = None) -> None:
        """Persist FAISS index to disk."""
        if self.store is None:
            raise ValueError("Vector store not initialized. Nothing to persist.")

        save_path = path or self.index_path
        if save_path:
            self.store.save_local(save_path)
            logger.info(f"Persisted FAISS index to {save_path}")

    def load(self, path: str) -> None:
        """Load FAISS index from disk."""
        self.store = FAISS.load_local(
            folder_path=path,
            embeddings=self.embeddings,
            allow_dangerous_deserialization=True,
        )
        self.index_path = path

    def delete_by_id(self, ids: list[str]) -> None:
        """Delete documents by ID.

        Note: FAISS doesn't support deletion natively.
        This is a limitation of the FAISS backend.
        """
        logger.warning(
            "FAISS does not support deletion by ID. "
            "Consider using Qdrant or ChromaDB for this feature."
        )
        raise NotImplementedError(
            "FAISS does not support document deletion. Use Qdrant or ChromaDB instead."
        )

    def list_metadata(self) -> list[dict]:
        """List all metadata in the store.

        Note: FAISS doesn't support metadata listing.
        Returns empty list.
        """
        logger.warning(
            "FAISS does not support metadata listing. "
            "Consider using Qdrant or ChromaDB for this feature."
        )
        return []

    def get_store_info(self) -> dict:
        """Get information about the FAISS store."""
        if self.store is None:
            return {
                "backend": "faiss",
                "status": "not_initialized",
                "document_count": 0,
            }

        # FAISS doesn't expose document count directly
        # We can get index size, but not document count
        return {
            "backend": "faiss",
            "status": "active",
            "index_path": self.index_path,
            "index_size": self.store.index.ntotal
            if hasattr(self.store, "index")
            else 0,
            "supports_metadata_listing": False,
            "supports_deletion": False,
            "supports_updates": False,
        }
