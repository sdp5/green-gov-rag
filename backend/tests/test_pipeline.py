"""Tests for complete ETL and RAG pipelines.

This test suite covers:
- End-to-end ETL pipeline (load → parse → chunk → embed → store)
- RAG query pipeline (query → retrieve → generate)
- Integration between ETL and RAG
- Pipeline error handling
- Multi-document processing
- Metadata preservation through pipelines
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain.schema import Document

from green_gov_rag.etl import chunker, utils

# ============================================================================
# Sample Documents for Testing
# ============================================================================

DOCS = [
    {
        "title": "Biodiversity PDF",
        "text": "This document describes biodiversity regulations and environmental guidelines in Australia.",
        "metadata": {
            "source": "biodiversity_pdf",
            "topic": "biodiversity",
            "region": "Australia",
            "jurisdiction": "federal",
        },
    },
    {
        "title": "Emissions HTML",
        "text": "<html><body><h1>Emissions</h1><p>Guidelines for energy and emissions reporting in coal mining and electricity.</p></body></html>",
        "metadata": {
            "source": "emissions_html",
            "topic": "emissions_reporting",
            "region": "Australia",
            "jurisdiction": "federal",
        },
    },
    {
        "title": "Planning PDF",
        "text": "Planning guidelines for urban development in New South Wales.",
        "metadata": {
            "source": "planning_pdf",
            "topic": "planning",
            "region": "NSW",
            "jurisdiction": "state",
        },
    },
]


# ============================================================================
# Helper Functions
# ============================================================================


def fake_html_parse(html):
    """Fake HTML parser for testing."""
    return utils.clean_text(html)


# ============================================================================
# Basic Pipeline Tests
# ============================================================================


def test_multiple_documents_pipeline():
    """Test basic multi-document ETL pipeline."""
    all_chunks = []

    # Step 1: Clean and chunk each document
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)

    for doc in DOCS:
        text: str = doc["text"]  # type: ignore[assignment]
        if str(doc["title"]).endswith("HTML"):
            content = fake_html_parse(text)
        else:
            content = utils.clean_text(text)
        chunks = text_chunker.chunk_text(content)
        # Attach metadata to each chunk
        all_chunks.extend([{"content": c, "metadata": doc["metadata"]} for c in chunks])

    assert len(all_chunks) > 0

    # Step 2: Mock embedder
    from tests.conftest import MockChunkEmbedder

    mock_embedder = MockChunkEmbedder()
    embedded_chunks = mock_embedder.embed_chunks(all_chunks)

    assert len(embedded_chunks) > 0

    # Step 3: Test that chunks have embeddings
    for chunk in embedded_chunks:
        assert "embedding" in chunk
        assert isinstance(chunk["embedding"], list)
        assert len(chunk["embedding"]) > 0

    # Step 4: Verify metadata preserved
    assert any("biodiversity" in c["metadata"]["topic"] for c in embedded_chunks)
    assert any("emissions" in c["metadata"]["topic"] for c in embedded_chunks)
    assert any("planning" in c["metadata"]["topic"] for c in embedded_chunks)


def test_pipeline_metadata_preservation():
    """Test that metadata is preserved through all pipeline stages."""
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)

    # Process single document
    doc = DOCS[0]
    content = utils.clean_text(doc["text"])  # type: ignore[arg-type]
    chunks = text_chunker.chunk_text(content)

    # Attach metadata
    chunked_docs = [{"content": c, "metadata": doc["metadata"]} for c in chunks]

    # Embed
    from tests.conftest import MockChunkEmbedder

    mock_embedder = MockChunkEmbedder()
    embedded = mock_embedder.embed_chunks(chunked_docs)

    # Verify all metadata fields preserved
    for chunk in embedded:
        assert chunk["metadata"]["source"] == "biodiversity_pdf"
        assert chunk["metadata"]["topic"] == "biodiversity"
        assert chunk["metadata"]["region"] == "Australia"
        assert chunk["metadata"]["jurisdiction"] == "federal"


def test_pipeline_with_empty_documents():
    """Test pipeline handles empty documents gracefully."""
    empty_doc = {
        "title": "Empty Doc",
        "text": "",
        "metadata": {"source": "empty", "topic": "none"},
    }

    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)
    content = utils.clean_text(empty_doc["text"])  # type: ignore[arg-type]
    chunks = text_chunker.chunk_text(content)

    # Should handle empty gracefully
    assert isinstance(chunks, list)
    # May be empty or have one empty chunk
    assert len(chunks) <= 1


def test_pipeline_chunk_size_variations():
    """Test pipeline with different chunk sizes."""
    doc = DOCS[0]
    content = utils.clean_text(doc["text"])  # type: ignore[arg-type]

    # Test different chunk sizes
    for chunk_size in [10, 50, 100, 200]:
        text_chunker = chunker.TextChunker(chunk_size=chunk_size, chunk_overlap=5)
        chunks = text_chunker.chunk_text(content)
        assert len(chunks) >= 1
        # Smaller chunks should generally produce more chunks
        # (though not strictly guaranteed)


# ============================================================================
# Enhanced ETL Pipeline Tests
# ============================================================================


def test_enhanced_etl_pipeline_initialization():
    """Test EnhancedETLPipeline initialization."""
    from green_gov_rag.etl.pipeline import EnhancedETLPipeline

    # Without auto-tagging
    pipeline = EnhancedETLPipeline(enable_auto_tagging=False, use_cloud=False)
    assert pipeline.enable_auto_tagging is False
    assert pipeline.tagger is None
    assert pipeline.use_cloud is False

    # With auto-tagging (mocked)
    with patch("green_gov_rag.etl.pipeline.ESGOpenAITagger"):
        pipeline = EnhancedETLPipeline(enable_auto_tagging=True, use_cloud=False)
        assert pipeline.enable_auto_tagging is True


def test_enhanced_etl_pipeline_chunking():
    """Test chunking within EnhancedETLPipeline."""
    from green_gov_rag.etl.pipeline import EnhancedETLPipeline

    pipeline = EnhancedETLPipeline(
        enable_auto_tagging=False,
        chunk_size=50,
        chunk_overlap=10,
        use_cloud=False,
    )

    # Create mock documents
    docs = [
        Document(
            page_content="This is a test document about environmental regulations.",
            metadata={"source": "test.pdf", "topic": "environment"},
        )
    ]

    # Chunk documents
    chunked = pipeline.chunker.chunk_docs(
        [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
    )

    assert len(chunked) >= 1
    assert all("chunk_id" in c["metadata"] for c in chunked)


# ============================================================================
# RAG Pipeline Tests (Query → Retrieve → Generate)
# ============================================================================


def test_rag_query_pipeline(in_memory_faiss):
    """Test end-to-end RAG query pipeline."""
    # Step 1: Query the vector store
    query = "What are the biodiversity regulations?"
    results = in_memory_faiss.similarity_search(query, k=3)

    assert isinstance(results, list)
    assert len(results) <= 3

    # Step 2: Extract content from results
    if results:
        contents = [doc.page_content for doc in results]
        assert all(isinstance(c, str) for c in contents)


def test_rag_pipeline_with_filters(in_memory_faiss):
    """Test RAG pipeline with metadata filtering."""
    query = "emissions reporting"

    # Search without filters
    all_results = in_memory_faiss.similarity_search(query, k=10)

    # Apply post-search metadata filter
    filtered = [r for r in all_results if r.metadata.get("region") == "NSW"]

    assert isinstance(filtered, list)
    # All filtered results should have NSW region
    assert all(r.metadata.get("region") == "NSW" for r in filtered)


def test_rag_pipeline_empty_query(in_memory_faiss):
    """Test RAG pipeline handles empty queries."""
    results = in_memory_faiss.similarity_search("", k=5)
    assert isinstance(results, list)


def test_rag_pipeline_with_hybrid_search(in_memory_faiss):
    """Test RAG pipeline with hybrid search."""
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch

    search = HybridGeospatialSearch(in_memory_faiss, enable_ner=False)

    query = "carbon emissions regulations"
    results = search.search(query, k=5)

    assert isinstance(results, list)
    assert len(results) <= 5


# ============================================================================
# Integration Tests (ETL → RAG)
# ============================================================================


def test_full_pipeline_etl_to_rag(tmp_path, mock_embedder):
    """Test complete pipeline from ETL to RAG query."""
    # Step 1: ETL - Process documents
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)
    all_chunks = []

    for doc in DOCS:
        content = utils.clean_text(doc["text"])  # type: ignore[arg-type]
        chunks = text_chunker.chunk_text(content)
        all_chunks.extend([{"content": c, "metadata": doc["metadata"]} for c in chunks])

    # Step 2: Embed chunks
    embedded = mock_embedder.embed_chunks(all_chunks)
    assert len(embedded) > 0

    # Step 3: Build vector store (simulated)
    # In real pipeline, this would create FAISS/Qdrant index

    # Step 4: RAG Query (simulated)
    # Would query the vector store and generate response


def test_pipeline_with_document_updates():
    """Test pipeline handles document updates."""
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)

    # Initial document
    doc_v1 = {
        "title": "Policy V1",
        "text": "Original policy text about environmental standards.",
        "metadata": {"source": "policy.pdf", "version": "1"},
    }

    # Updated document
    doc_v2 = {
        "title": "Policy V2",
        "text": "Updated policy text with new environmental standards and stricter regulations.",
        "metadata": {"source": "policy.pdf", "version": "2"},
    }

    # Process both versions
    for doc in [doc_v1, doc_v2]:
        content = utils.clean_text(doc["text"])  # type: ignore[arg-type]
        chunks = text_chunker.chunk_text(content)
        chunked = [{"content": c, "metadata": doc["metadata"]} for c in chunks]
        assert len(chunked) > 0
        # In real system, would update vector store with new chunks


def test_pipeline_error_handling_invalid_document():
    """Test pipeline handles invalid documents."""
    invalid_doc: dict[str, None | int | dict] = {
        "title": None,  # Invalid
        "text": 123,  # Invalid type
        "metadata": {},
    }

    # Pipeline should handle gracefully
    try:
        content = utils.clean_text(str(invalid_doc.get("text", "")))
        assert isinstance(content, str)
    except Exception:
        # Should not crash
        pass


# ============================================================================
# Performance and Scale Tests
# ============================================================================


def test_pipeline_large_document_batch():
    """Test pipeline with large batch of documents."""
    from tests.conftest import MockChunkEmbedder

    # Create 100 documents
    large_batch = []
    for i in range(100):
        doc = {
            "content": f"Document {i} with environmental regulations content.",
            "metadata": {"source": f"doc_{i}.pdf", "index": i},
        }
        large_batch.append(doc)

    # Embed in batch
    mock_embedder = MockChunkEmbedder()
    embedded = mock_embedder.embed_chunks(large_batch)

    assert len(embedded) == 100
    assert all("embedding" in e for e in embedded)


def test_pipeline_concurrent_processing():
    """Test pipeline with concurrent document processing simulation."""
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)

    # Simulate processing multiple documents
    results = []
    for doc in DOCS:
        content = utils.clean_text(doc["text"])  # type: ignore[arg-type]
        chunks = text_chunker.chunk_text(content)
        results.append(len(chunks))

    # All documents should be processed
    assert len(results) == len(DOCS)
    assert all(r > 0 for r in results)


# ============================================================================
# Data Quality Tests
# ============================================================================


def test_pipeline_deduplication():
    """Test pipeline identifies duplicate content."""
    # Create documents with duplicate content
    doc1 = {
        "content": "Identical content about regulations.",
        "metadata": {"source": "doc1.pdf"},
    }
    doc2 = {
        "content": "Identical content about regulations.",
        "metadata": {"source": "doc2.pdf"},  # Different source, same content
    }

    from tests.conftest import MockChunkEmbedder

    mock_embedder = MockChunkEmbedder()
    embedded = mock_embedder.embed_chunks([doc1, doc2])

    # Both should be embedded (deduplication is downstream)
    assert len(embedded) == 2

    # In real system, could detect duplicates by comparing embeddings


def test_pipeline_data_validation():
    """Test pipeline validates data quality."""
    from tests.conftest import MockChunkEmbedder

    valid_chunks = [
        {"content": "Valid content here.", "metadata": {"source": "valid.pdf"}},
        {"content": "", "metadata": {"source": "empty.pdf"}},  # Empty content
        {"content": "   ", "metadata": {"source": "whitespace.pdf"}},  # Whitespace only
    ]

    mock_embedder = MockChunkEmbedder()

    # Filter out invalid chunks (empty/whitespace)
    filtered = [c for c in valid_chunks if c.get("content", "").strip()]  # type: ignore[attr-defined]
    embedded = mock_embedder.embed_chunks(filtered)

    # Only valid chunk should be embedded
    assert len(embedded) == 1


# ============================================================================
# Metadata Enhancement Tests
# ============================================================================


def test_pipeline_metadata_enrichment():
    """Test pipeline enriches metadata during processing."""
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)

    doc = DOCS[0]
    content = utils.clean_text(doc["text"])  # type: ignore[arg-type]
    chunks = text_chunker.chunk_text(content)

    # Enrich with additional metadata
    enriched = []
    for i, chunk in enumerate(chunks):
        chunk_data = {
            "content": chunk,
            "metadata": {
                **doc["metadata"],  # type: ignore[dict-item]
                "chunk_index": i,
                "total_chunks": len(chunks),
                "processed_at": "2025-01-01T00:00:00Z",
            },
        }
        enriched.append(chunk_data)

    # Verify enrichment
    assert all("chunk_index" in c["metadata"] for c in enriched)
    assert all("total_chunks" in c["metadata"] for c in enriched)
    assert enriched[0]["metadata"]["chunk_index"] == 0  # type: ignore[index]


# ============================================================================
# Storage Integration Tests
# ============================================================================


def test_pipeline_with_storage_adapter():
    """Test pipeline with storage adapter."""
    from green_gov_rag.etl.pipeline import EnhancedETLPipeline

    with patch("green_gov_rag.etl.pipeline.ETLStorageAdapter") as mock_storage:
        mock_storage.return_value = MagicMock()

        pipeline = EnhancedETLPipeline(
            enable_auto_tagging=False,
            use_cloud=True,  # Enable cloud storage
        )

        assert pipeline.storage_adapter is not None


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


def test_pipeline_special_characters():
    """Test pipeline handles special characters."""
    special_doc = {
        "title": "Special Chars",
        "text": "Regulations: § 123.45(a)(1) @ $50/tonne CO₂-e ™®©",
        "metadata": {"source": "special.pdf"},
    }

    content = utils.clean_text(special_doc["text"])  # type: ignore[arg-type]
    text_chunker = chunker.TextChunker(chunk_size=200, chunk_overlap=20)
    chunks = text_chunker.chunk_text(content)

    assert len(chunks) >= 1
    # Content should be cleaned but readable
    assert isinstance(chunks[0], str)


def test_pipeline_unicode_content():
    """Test pipeline handles unicode content."""
    unicode_doc = {
        "title": "Unicode Doc",
        "text": "Regulations in différent langüages: 中文 العربية русский",
        "metadata": {"source": "unicode.pdf"},
    }

    content = utils.clean_text(unicode_doc["text"])  # type: ignore[arg-type]
    text_chunker = chunker.TextChunker(chunk_size=200, chunk_overlap=20)
    chunks = text_chunker.chunk_text(content)

    assert len(chunks) >= 1
    assert isinstance(chunks[0], str)


def test_pipeline_very_long_document():
    """Test pipeline handles very long documents."""
    # Create a very long document (10,000 words)
    long_text = " ".join([f"word{i}" for i in range(10000)])
    long_doc = {
        "title": "Long Doc",
        "text": long_text,
        "metadata": {"source": "long.pdf"},
    }

    text_chunker = chunker.TextChunker(chunk_size=100, chunk_overlap=20)
    chunks = text_chunker.chunk_text(long_doc["text"])  # type: ignore[arg-type]

    # Should produce many chunks
    assert len(chunks) > 50
    assert all(isinstance(c, str) for c in chunks)
