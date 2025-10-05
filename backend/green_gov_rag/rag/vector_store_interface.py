"""Abstract interface for vector stores."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain.docstore.document import Document
from langchain_core.embeddings import Embeddings


class VectorStoreInterface(ABC):
    """Abstract base class for vector store implementations.

    Provides a common interface for FAISS, Qdrant, ChromaDB, etc.
    """

    def __init__(self, embeddings: Embeddings, **kwargs: Any):
        """Initialize vector store.

        Args:
            embeddings: Embeddings model to use
            **kwargs: Implementation-specific arguments
        """
        self.embeddings = embeddings

    @abstractmethod
    def add_documents(self, docs: list[Document]) -> None:
        """Add documents to the vector store.

        Args:
            docs: List of LangChain Document objects
        """
        pass

    @abstractmethod
    def build_store(self, chunks: list[dict]) -> None:
        """Build vector store from list of chunks.

        Args:
            chunks: List of dicts with 'content' and 'metadata' keys
        """
        pass

    @abstractmethod
    def add_chunks(self, chunks: list[dict]) -> None:
        """Add chunks to existing store.

        Args:
            chunks: List of dicts with 'content' and 'metadata' keys
        """
        pass

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        metadata_filters: dict | None = None,
    ) -> list[Document]:
        """Perform similarity search with optional metadata filtering.

        Args:
            query: Query string
            k: Number of results to return
            metadata_filters: Optional metadata filters

        Returns:
            List of Document objects
        """
        pass

    @abstractmethod
    def persist(self, path: str | None = None) -> None:
        """Persist vector store to disk/database.

        Args:
            path: Optional path for persistence
        """
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load vector store from disk/database.

        Args:
            path: Path to load from
        """
        pass

    @abstractmethod
    def delete_by_id(self, ids: list[str]) -> None:
        """Delete documents by ID.

        Args:
            ids: List of document IDs to delete
        """
        pass

    @abstractmethod
    def list_metadata(self) -> list[dict]:
        """List all metadata in the store.

        Returns:
            List of metadata dictionaries
        """
        pass

    @abstractmethod
    def get_store_info(self) -> dict:
        """Get information about the vector store.

        Returns:
            Dictionary with store statistics (count, size, etc.)
        """
        pass
