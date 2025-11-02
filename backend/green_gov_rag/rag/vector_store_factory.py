"""Factory for creating vector store instances."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.embeddings import Embeddings

from green_gov_rag.config import settings
from green_gov_rag.rag.vector_store_interface import VectorStoreInterface

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class VectorStoreFactory:
    """Factory for creating vector store instances based on configuration."""

    @staticmethod
    def create_vector_store(
        embeddings: Embeddings,
        store_type: str | None = None,
        **kwargs,
    ) -> VectorStoreInterface:
        """Create a vector store instance.

        Args:
            embeddings: Embeddings model to use
            store_type: Type of store ('faiss', 'qdrant', 'chromadb').
                       If None, uses settings.vector_store_type
            **kwargs: Additional arguments for specific store implementations

        Returns:
            VectorStoreInterface: Initialized vector store

        Raises:
            ValueError: If store_type is not supported

        Examples:
            >>> from green_gov_rag.rag.embeddings import ChunkEmbedder
            >>> embeddings = ChunkEmbedder().embedder
            >>> store = VectorStoreFactory.create_vector_store(embeddings)

            >>> # Explicitly choose Qdrant
            >>> store = VectorStoreFactory.create_vector_store(
            ...     embeddings,
            ...     store_type='qdrant',
            ...     url='http://localhost:6333'
            ... )
        """
        store_type = store_type or settings.vector_store_type

        logger.info(f"Creating vector store: {store_type}")

        if store_type == "faiss":
            return VectorStoreFactory._create_faiss_store(embeddings, **kwargs)
        elif store_type == "qdrant":
            return VectorStoreFactory._create_qdrant_store(embeddings, **kwargs)
        elif store_type == "chromadb":
            return VectorStoreFactory._create_chroma_store(embeddings, **kwargs)
        else:
            raise ValueError(
                f"Unsupported vector store type: {store_type}. "
                f"Supported types: faiss, qdrant, chromadb"
            )

    @staticmethod
    def _create_faiss_store(
        embeddings: Embeddings,
        **kwargs,
    ) -> VectorStoreInterface:
        """Create FAISS vector store."""
        from green_gov_rag.rag.stores import FAISSVectorStore

        index_path = kwargs.get("index_path") or settings.vector_store_path

        return FAISSVectorStore(
            embeddings=embeddings,
            index_path=index_path,
            **kwargs,
        )

    @staticmethod
    def _create_qdrant_store(
        embeddings: Embeddings,
        **kwargs,
    ) -> VectorStoreInterface:
        """Create Qdrant vector store."""
        from green_gov_rag.rag.stores import QdrantVectorStore

        url: str = kwargs.pop("url", None) or settings.qdrant_url or ""
        if not url:
            raise ValueError(
                "Qdrant URL not configured. Set QDRANT_URL in environment or pass url parameter."
            )

        api_key: str | None = kwargs.pop("api_key", None) or settings.qdrant_api_key
        collection_name: str = str(kwargs.pop("collection_name", "greengovrag"))

        return QdrantVectorStore(
            embeddings=embeddings,
            url=url,
            api_key=api_key,
            collection_name=collection_name,
            **kwargs,  # Any remaining kwargs
        )

    @staticmethod
    def _create_chroma_store(
        embeddings: Embeddings,
        **kwargs,
    ) -> VectorStoreInterface:
        """Create ChromaDB vector store."""
        # TODO: Implement ChromaDB store
        raise NotImplementedError(
            "ChromaDB support coming soon. Use 'faiss' or 'qdrant' for now."
        )

    @staticmethod
    def get_available_stores() -> list[str]:
        """Get list of available vector store types.

        Returns:
            List of supported store types
        """
        available = ["faiss"]

        # Check if Qdrant is available
        try:
            import qdrant_client  # noqa: F401

            available.append("qdrant")
        except ImportError:
            pass

        # Check if ChromaDB is available
        try:
            import chromadb  # noqa: F401

            available.append("chromadb")
        except ImportError:
            pass

        return available

    @staticmethod
    def validate_config(store_type: str | None = None) -> dict:
        """Validate configuration for a vector store type.

        Args:
            store_type: Type to validate, or None for current config

        Returns:
            Dictionary with validation results

        Examples:
            >>> VectorStoreFactory.validate_config('qdrant')
            {
                'valid': True,
                'store_type': 'qdrant',
                'issues': [],
                'config': {'url': 'http://localhost:6333', ...}
            }
        """
        store_type = store_type or settings.vector_store_type
        issues = []
        config: dict[str, str | None] = {}

        if store_type == "faiss":
            config["index_path"] = settings.vector_store_path
            if not settings.vector_store_path:
                issues.append("VECTOR_STORE_PATH not configured")

        elif store_type == "qdrant":
            config["url"] = settings.qdrant_url
            config["api_key"] = "***" if settings.qdrant_api_key else None

            if not settings.qdrant_url:
                issues.append("QDRANT_URL not configured")

            # Check if Qdrant client is installed
            try:
                import qdrant_client  # noqa: F401
            except ImportError:
                issues.append(
                    "qdrant_client not installed. "
                    "Install with: pip install qdrant-client langchain-qdrant"
                )

        elif store_type == "chromadb":
            issues.append("ChromaDB not yet implemented")

        else:
            issues.append(f"Unknown store type: {store_type}")

        return {
            "valid": len(issues) == 0,
            "store_type": store_type,
            "issues": issues,
            "config": config,
        }


# Convenience function
def create_vector_store(
    embeddings: Embeddings,
    store_type: str | None = None,
    **kwargs,
) -> VectorStoreInterface:
    """Create a vector store instance.

    Convenience wrapper around VectorStoreFactory.create_vector_store()

    Args:
        embeddings: Embeddings model
        store_type: Type of store (faiss, qdrant, chromadb)
        **kwargs: Additional store-specific arguments

    Returns:
        VectorStoreInterface: Initialized vector store
    """
    return VectorStoreFactory.create_vector_store(embeddings, store_type, **kwargs)
