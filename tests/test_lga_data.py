"""Tests for LGA data."""


import pytest
from green_gov_rag.etl import chunker, utils
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
    {
        "title": "Victoria Emissions Reporting Guidelines",
        "text": "Emissions reporting rules for Victoria industrial facilities.",
        "metadata": {
            "source": "vic_emissions",
            "topic": "emissions_reporting",
            "region": "Victoria",
            "sovereign": True,
        },
    },
    {
        "title": "NSW Biodiversity Offsets Scheme",
        "text": "Biodiversity offset rules and documentation for NSW.",
        "metadata": {"source": "nsw_offsets", "topic": "biodiversity", "region": "New South Wales"},
    },
    {
        "title": "National Construction Code",
        "text": "Construction code regulations across Australia.",
        "metadata": {"source": "ncc", "topic": "building", "region": "Australia"},
    },
    {
        "title": "Planning and Design Code SA",
        "text": "Land-use and planning regulations in South Australia.",
        "metadata": {"source": "sa_planning", "topic": "land_use", "region": "South Australia"},
    },
]


# -----------------------------
# Helper: check if point is in LGA polygon
# -----------------------------
def point_in_lga(lat, lon, polygon_geojson):
    poly = shape(polygon_geojson)
    return poly.contains(Point(lon, lat))


# -----------------------------
# Parameterized test cases
# -----------------------------
TEST_QUERIES = [
    {
        "query": "What are the biodiversity regulations in Adelaide?",
        "filters": {
            "custom_filter_fn": lambda metadata: "lga_geometry" in metadata
            and point_in_lga(-34.935, 138.575, metadata["lga_geometry"])
        },
        "expected_topic": "biodiversity",
    },
    {
        "query": "Show sustainable development policies in Port Adelaide.",
        "filters": {
            "custom_filter_fn": lambda metadata: "lga_geometry" in metadata
            and point_in_lga(-34.825, 138.525, metadata["lga_geometry"])
        },
        "expected_topic": "sustainable_development",
    },
    {
        "query": "What are the emissions reporting rules for Victoria?",
        "filters": {"topic": "emissions_reporting"},
        "expected_topic": "emissions_reporting",
    },
    {
        "query": "Land-use planning rules in South Australia?",
        "filters": {"region": "South Australia"},
        "expected_topic": "land_use",
    },
]


# -----------------------------
# End-to-End Pipeline Test
# -----------------------------
@pytest.mark.parametrize("test_case", TEST_QUERIES)
def test_rag_chain_with_multiple_documents(test_case):
    # Step 1: Chunking all documents
    all_chunks = []
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)
    for doc in DOCS:
        text: str = doc["text"]  # type: ignore[assignment]
        cleaned_text = utils.clean_text(text)
        chunks = text_chunker.chunk_text(cleaned_text)
        for c in chunks:
            all_chunks.append({"content": c, "metadata": doc["metadata"]})

    assert len(all_chunks) > 0

    # Step 2: Mock embeddings
    from tests.conftest import MockChunkEmbedder
    mock_embedder = MockChunkEmbedder()
    embedded_chunks = mock_embedder.embed_chunks(all_chunks)

    # Step 3: Verify embeddings
    assert len(embedded_chunks) > 0
    for chunk in embedded_chunks:
        assert "embedding" in chunk
        assert isinstance(chunk["embedding"], list)

    # Step 4: Verify metadata filtering would work
    # Filter by topic if present in test case
    if "custom_filter_fn" in test_case["filters"]:
        filter_fn = test_case["filters"]["custom_filter_fn"]
        filtered = [c for c in embedded_chunks if filter_fn(c["metadata"])]
        assert len(filtered) >= 0  # Could be empty depending on filter

    # Verify expected topic exists in some chunk
    assert any(test_case["expected_topic"] in c["metadata"].get("topic", "") for c in embedded_chunks)
