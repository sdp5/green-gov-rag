"""Tests for complete pipeline."""

from green_gov_rag.etl import chunker, utils

# -----------------------------
# Sample document texts
# -----------------------------
DOCS = [
    {
        "title": "Biodiversity PDF",
        "text": "This document describes biodiversity regulations and environmental guidelines in Australia.",
        "metadata": {"source": "biodiversity_pdf", "topic": "biodiversity", "region": "Australia"},
    },
    {
        "title": "Emissions HTML",
        "text": "<html><body><h1>Emissions</h1><p>Guidelines for energy and emissions reporting in coal mining and electricity.</p></body></html>",
        "metadata": {
            "source": "emissions_html",
            "topic": "emissions_reporting",
            "region": "Australia",
        },
    },
    {
        "title": "Planning PDF",
        "text": "Planning guidelines for urban development in New South Wales.",
        "metadata": {"source": "planning_pdf", "topic": "planning", "region": "NSW"},
    },
]


# -----------------------------
# Helper: fake HTML parser
# -----------------------------
def fake_html_parse(html):
    return utils.clean_text(html)


# -----------------------------
# End-to-End Pipeline Test with multiple files
# -----------------------------
def test_multiple_documents_pipeline():
    all_chunks = []
    # -----------------------------
    # Step 1: Clean and chunk each document
    # -----------------------------
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

    # -----------------------------
    # Step 2: Mock embedder
    # -----------------------------
    from tests.conftest import MockChunkEmbedder
    mock_embedder = MockChunkEmbedder()
    embedded_chunks = mock_embedder.embed_chunks(all_chunks)

    assert len(embedded_chunks) > 0

    # -----------------------------
    # Step 3: Test that chunks have embeddings
    # -----------------------------
    for chunk in embedded_chunks:
        assert "embedding" in chunk
        assert isinstance(chunk["embedding"], list)
        assert len(chunk["embedding"]) > 0

    # -----------------------------
    # Step 4: Verify metadata preserved
    # -----------------------------
    assert any("biodiversity" in c["metadata"]["topic"] for c in embedded_chunks)
    assert any("emissions" in c["metadata"]["topic"] for c in embedded_chunks)
    assert any("planning" in c["metadata"]["topic"] for c in embedded_chunks)
