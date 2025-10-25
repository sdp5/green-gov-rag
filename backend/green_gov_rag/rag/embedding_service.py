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
    from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Singleton service for lazy-loading embedding models."""

    _model: SentenceTransformer | None = None
    _model_name: str | None = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Get or load the embedding model.

        Loads the model on first access and caches it for subsequent calls.
        Uses the model specified in settings.embedding_model.

        Returns
        -------
            SentenceTransformer: The loaded embedding model

        """
        # Load model if not already loaded or if model name changed
        if cls._model is None or cls._model_name != settings.embedding_model:
            from sentence_transformers import SentenceTransformer

            cls._model_name = settings.embedding_model
            cls._model = SentenceTransformer(cls._model_name)

        return cls._model

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
        model = cls.get_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

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
        model = cls.get_model()
        embedding = model.encode(query, show_progress_bar=False)
        return embedding.tolist()

    @classmethod
    def get_embedding_dimension(cls) -> int:
        """Get the dimension of the embedding model.

        Returns
        -------
            int: Embedding dimension (e.g., 384, 768, 1024)

        Raises
        ------
            RuntimeError: If embedding dimension cannot be determined

        """
        model = cls.get_model()
        dimension = model.get_sentence_embedding_dimension()
        if dimension is None:
            raise RuntimeError("Could not determine embedding dimension from model")
        return dimension

    @classmethod
    def clear_model(cls) -> None:
        """Clear the model from memory.

        Useful after batch operations to free up RAM (~1.5GB for BGE-large).
        The model will be reloaded on next access.

        Example:
        -------
            # Process large batch
            EmbeddingService.embed_texts(large_batch)

            # Free memory
            EmbeddingService.clear_model()

        """
        if cls._model is not None:
            del cls._model
            cls._model = None
            gc.collect()

    @classmethod
    def is_loaded(cls) -> bool:
        """Check if model is currently loaded in memory.

        Returns
        -------
            bool: True if model is loaded, False otherwise

        """
        return cls._model is not None

    @classmethod
    def get_model_info(cls) -> dict[str, str | int | bool]:
        """Get information about the current embedding model.

        Returns
        -------
            Dictionary with model information:
            - model_name: Name of the model
            - is_loaded: Whether model is loaded in memory
            - dimension: Embedding dimension (if loaded)

        """
        info: dict[str, str | int | bool] = {
            "model_name": settings.embedding_model,
            "is_loaded": cls.is_loaded(),
        }

        if cls.is_loaded():
            info["dimension"] = cls.get_embedding_dimension()

        return info


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
