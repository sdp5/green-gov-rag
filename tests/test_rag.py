"""Tests for RAG components."""

from __future__ import annotations

import pytest

SAMPLE_CHUNKS = [
    {"content": "Carbon emissions report for NSW", "metadata": {"region": "NSW"}},
    {"content": "Biodiversity conservation guidelines", "metadata": {"region": "SA"}},
]


def test_vector_store_build(in_memory_faiss):
    """Test vector store is ready."""
    assert in_memory_faiss is not None
    assert hasattr(in_memory_faiss, "similarity_search")
    results = in_memory_faiss.similarity_search("Carbon report", k=1)
    assert len(results) <= 1


@pytest.mark.skip(reason="Fixture interaction issue when running full test suite")
def test_rag_chain_basic(in_memory_faiss, mock_embedder):
    """Test basic RAG chain."""
    from green_gov_rag.rag.rag_chain import RAGChain

    rag = RAGChain(in_memory_faiss, mock_embedder)
    # Mock would need a run method - skip for now or implement
    assert rag.vector_store is not None


@pytest.mark.skip(reason="Fixture interaction issue when running full test suite")
def test_rag_chain_with_filters(in_memory_faiss, mock_embedder):
    """Test RAG with metadata filters."""
    results = in_memory_faiss.similarity_search(
        "Biodiversity",
        k=2,
        filter={"region": "SA"},
    )
    assert isinstance(results, list)


def test_embeddings_output_shape(mock_embedder, sample_chunks):
    """Test embeddings shape."""
    embedded = mock_embedder.embed_chunks(sample_chunks[:2])
    for e in embedded:
        assert "embedding" in e
        assert isinstance(e["embedding"], list)
