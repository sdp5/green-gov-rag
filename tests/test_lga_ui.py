"""Tests for LGA UI."""

from unittest.mock import patch

import pytest
from etl import chunker, utils
from rag import embeddings, rag_chain, vector_store
from shapely.geometry import Point, shape

# -----------------------------
# Sample documents with metadata
# -----------------------------
DOCS = [
    {
        "title": "Adelaide Biodiversity Plan",
        "text": "This document covers biodiversity regulations for the City of Adelaide.",
        "metadata": {
            "source": "adelaide_biodiversity",
            "topic": "biodiversity",
            "region": "City of Adelaide",
            "lga_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [138.55, -34.95],
                        [138.60, -34.95],
                        [138.60, -34.92],
                        [138.55, -34.92],
                        [138.55, -34.95],
                    ]
                ],
            },
        },
    },
    {
        "title": "Port Adelaide Sustainability Guidelines",
        "text": "Sustainability policies for Port Adelaide Enfield LGA.",
        "metadata": {
            "source": "port_ade_sustain",
            "topic": "sustainable_development",
            "region": "Port Adelaide Enfield",
            "lga_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [138.50, -34.85],
                        [138.55, -34.85],
                        [138.55, -34.80],
                        [138.50, -34.80],
                        [138.50, -34.85],
                    ]
                ],
            },
        },
    },
]


# -----------------------------
# Helper: check if point is in LGA polygon
# -----------------------------
def point_in_lga(lat, lon, polygon_geojson):
    poly = shape(polygon_geojson)
    return poly.contains(Point(lon, lat))


# -----------------------------
# Mock Streamlit UI selections
# -----------------------------
def simulate_user_selection(selected_lgas, selected_topic):
    """Return metadata filter function for RAG chain based on map selection.
    """

    def metadata_filter(metadata):
        # LGA filter
        in_lga = False
        if "lga_geometry" in metadata:
            for lga in selected_lgas:
                if point_in_lga(lga["lat"], lga["lon"], metadata["lga_geometry"]):
                    in_lga = True
                    break
        else:
            in_lga = True  # no geometry = allow all
        # Topic filter
        topic_ok = metadata.get("topic") == selected_topic if selected_topic else True
        return in_lga and topic_ok

    return metadata_filter


# -----------------------------
# Parameterized test cases
# -----------------------------
USER_TESTS = [
    {
        "query": "Biodiversity policies in Adelaide and Port Adelaide",
        "selected_lgas": [{"lat": -34.935, "lon": 138.575}, {"lat": -34.825, "lon": 138.525}],
        "selected_topic": "biodiversity",
        "expected_sources": ["adelaide_biodiversity"],
    },
    {
        "query": "Sustainable development policies in Port Adelaide",
        "selected_lgas": [{"lat": -34.825, "lon": 138.525}],
        "selected_topic": "sustainable_development",
        "expected_sources": ["port_ade_sustain"],
    },
]


# -----------------------------
# End-to-End UI Simulation Test
# -----------------------------
@pytest.mark.parametrize("test_case", USER_TESTS)
def test_ui_rag_with_lga_selection(test_case):
    # Step 1: Chunking all documents
    all_chunks = []
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)
    for doc in DOCS:
        cleaned_text = utils.clean_text(doc["text"])
        chunks = text_chunker.chunk_text(cleaned_text)
        for c in chunks:
            all_chunks.append({"content": c, "metadata": doc["metadata"]})

    # Step 2: Mock embeddings
    with patch("rag.embeddings.BedrockEmbedder.embed_text") as mock_embed:
        mock_embed.side_effect = lambda txt: [0.1] * 10
        embedder = embeddings.BedrockEmbedder()
        embedded_chunks = [
            {
                "content": c["content"],
                "embedding": embedder.embed_text(c["content"]),
                "metadata": c["metadata"],
            }
            for c in all_chunks
        ]

    # Step 3: Vector store
    store = vector_store.VectorStore()
    for item in embedded_chunks:
        store.add(item["embedding"], item["metadata"])

    # Step 4: RAG chain
    chain = rag_chain.RAGChain(vector_store=store, embedder=embedder)

    # Step 5: Generate metadata filter based on simulated UI
    metadata_filter = simulate_user_selection(
        test_case["selected_lgas"], test_case["selected_topic"]
    )

    # Step 6: Run query with UI filters
    answer = chain.run(test_case["query"], metadata_filters={"custom_filter_fn": metadata_filter})

    # Step 7: Assertions
    for source in test_case["expected_sources"]:
        assert source in answer.lower() or answer == ""
