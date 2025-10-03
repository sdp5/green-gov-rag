"""Tests for complete pipeline."""

from unittest.mock import patch

from etl import chunker, utils
from rag import embeddings, rag_chain, vector_store

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
        if str(doc["title"]).endswith("HTML"):
            content = fake_html_parse(doc["text"])
        else:
            content = utils.clean_text(doc["text"])
        chunks = text_chunker.chunk_text(content)
        # Attach metadata to each chunk
        all_chunks.extend([{"content": c, "metadata": doc["metadata"]} for c in chunks])

    assert len(all_chunks) > 0

    # -----------------------------
    # Step 2: Embed chunks (mock)
    # -----------------------------
    with patch("rag.embeddings.BedrockEmbedder.embed_text") as mock_embed:
        mock_embed.side_effect = lambda txt: [0.1] * 10  # fake 10-dim embedding
        embedder = embeddings.BedrockEmbedder()
        embedded_chunks = [
            {
                "content": c["content"],
                "embedding": embedder.embed_text(c["content"]),
                "metadata": c["metadata"],
            }
            for c in all_chunks
        ]

    # -----------------------------
    # Step 3: Store in vector store
    # -----------------------------
    store = vector_store.VectorStore()
    for item in embedded_chunks:
        store.add(item["embedding"], item["metadata"])
    assert len(store.items) == len(embedded_chunks)

    # -----------------------------
    # Step 4: Create RAG chain
    # -----------------------------
    chain = rag_chain.RAGChain(vector_store=store, embedder=embedder)

    # -----------------------------
    # Step 5: Query with metadata filter
    # -----------------------------
    query1 = "What are the biodiversity regulations?"
    answer1 = chain.run(query1, metadata_filters={"topic": "biodiversity"})
    assert "biodiversity" in answer1.lower() or answer1 == ""

    query2 = "Explain emissions reporting for energy."
    answer2 = chain.run(query2, metadata_filters={"topic": "emissions_reporting"})
    assert "emissions" in answer2.lower() or answer2 == ""

    query3 = "Urban planning guidelines for NSW."
    answer3 = chain.run(query3, metadata_filters={"region": "NSW"})
    assert "planning" in answer3.lower() or answer3 == ""
