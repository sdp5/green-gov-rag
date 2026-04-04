"""Lazy-loading embedding service for memory optimization.

This module provides a singleton embedding service that loads models
on-demand and can free memory when not in use. Particularly useful
for large embedding models like BGE-large (1.5GB) in memory-constrained
environments.

Usage:
    from green_gov_rag.rag.embedding_service import EmbeddingService

    # Get embeddings (model loads automatically)
    embeddings = EmbeddingService.embed_texts(["text1", "text2"])

    # Clear model from memory after batch operations
    EmbeddingService.clear_model()
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

from green_gov_rag.config import settings

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings


class EmbeddingService:
    """Singleton service for lazy-loading embedding models.

    Works with any provider supported by ``create_embeddings()`` —
    HuggingFace, Azure OpenAI, OpenAI, or Bedrock.  The LangChain
    ``Embeddings`` interface is used internally so provider-specific
    details are abstracted away.
    """

    _embedder: Embeddings | None = None
    _model_name: str | None = None
    _provider: str | None = None

    @classmethod
    def get_embedder(cls) -> Embeddings:
        """Get or create the LangChain Embeddings instance.

        Lazily creates the embedder on first access.  Recreates if the
        configured model or provider has changed.

        Returns
        -------
            LangChain ``Embeddings`` instance

        """
        current_model = settings.embedding_model
        current_provider = settings.embedding_provider

        if (
            cls._embedder is None
            or cls._model_name != current_model
            or cls._provider != current_provider
        ):
            from green_gov_rag.rag.embeddings import create_embeddings

            cls._model_name = current_model
            cls._provider = current_provider
            cls._embedder = create_embeddings(current_provider, current_model)

        return cls._embedder

    @classmethod
    def embed_texts(cls, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
        ----
            texts: List of text strings to embed

        Returns:
        -------
            List of embedding vectors (each is a list of floats)

        """
        embedder = cls.get_embedder()
        return embedder.embed_documents(texts)

    @classmethod
    def embed_query(cls, query: str) -> list[float]:
        """Generate embedding for a single query.

        Args:
        ----
            query: Text string to embed

        Returns:
        -------
            Embedding vector as list of floats

        """
        embedder = cls.get_embedder()
        return embedder.embed_query(query)

    @classmethod
    def get_embedding_dimension(cls) -> int:
        """Get the dimension of the embedding model.

        Returns
        -------
            int: Embedding dimension (e.g., 384, 768, 3072)

        """
        return settings.embedding_dimensions

    @classmethod
    def clear_model(cls) -> None:
        """Clear the embedder from memory.

        Useful after batch operations to free up RAM.
        The embedder will be recreated on next access.
        """
        if cls._embedder is not None:
            del cls._embedder
            cls._embedder = None
            gc.collect()

    @classmethod
    def is_loaded(cls) -> bool:
        """Check if embedder is currently loaded in memory."""
        return cls._embedder is not None

    @classmethod
    def get_model_info(cls) -> dict[str, str | int | bool]:
        """Get information about the current embedding model.

        Returns
        -------
            Dictionary with model information

        """
        return {
            "model_name": settings.embedding_model,
            "provider": settings.embedding_provider,
            "is_loaded": cls.is_loaded(),
            "dimension": settings.embedding_dimensions,
        }


# Convenience functions for backwards compatibility
def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Convenience wrapper for EmbeddingService.embed_texts().

    Args:
    ----
        texts: List of text strings to embed

    Returns:
    -------
        List of embedding vectors

    """
    return EmbeddingService.embed_texts(texts)


def get_query_embedding(query: str) -> list[float]:
    """Generate embedding for a single query.

    Convenience wrapper for EmbeddingService.embed_query().

    Args:
    ----
        query: Text string to embed

    Returns:
    -------
        Embedding vector

    """
    return EmbeddingService.embed_query(query)
