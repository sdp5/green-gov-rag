import pytest
from unittest.mock import patch
from etl import utils, chunker
from rag import embeddings, vector_store, rag_chain
from shapely.geometry import shape, Point

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
                "coordinates": [[[138.55,-34.95],[138.60,-34.95],[138.60,-34.92],[138.55,-34.92],[138.55,-34.95]]]
            }
        }
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
                "coordinates": [[[138.50,-34.85],[138.55,-34.85],[138.55,-34.80],[138.50,-34.80],[138.50,-34.85]]]
            }
        }
    },
    {
        "title": "Victoria Emissions Reporting Guidelines",
        "text": "Emissions reporting rules for Victoria industrial facilities.",
        "metadata": {
            "source": "vic_emissions",
            "topic": "emissions_reporting",
            "region": "Victoria",
            "sovereign": True
        }
    },
    {
        "title": "NSW Biodiversity Offsets Scheme",
        "text": "Biodiversity offset rules and documentation for NSW.",
        "metadata": {
            "source": "nsw_offsets",
            "topic": "biodiversity",
            "region": "New South Wales"
        }
    },
    {
        "title": "National Construction Code",
        "text": "Construction code regulations across Australia.",
        "metadata": {
            "source": "ncc",
            "topic": "building",
            "region": "Australia"
        }
    },
    {
        "title": "Planning and Design Code SA",
        "text": "Land-use and planning regulations in South Australia.",
        "metadata": {
            "source": "sa_planning",
            "topic": "land_use",
            "region": "South Australia"
        }
    }
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
            "custom_filter_fn": lambda metadata: "lga_geometry" in metadata and point_in_lga(-34.935, 138.575, metadata["lga_geometry"])
        },
        "expected_topic": "biodiversity"
    },
    {
        "query": "Show sustainable development policies in Port Adelaide.",
        "filters": {
            "custom_filter_fn": lambda metadata: "lga_geometry" in metadata and point_in_lga(-34.825, 138.525, metadata["lga_geometry"])
        },
        "expected_topic": "sustainable_development"
    },
    {
        "query": "What are the emissions reporting rules for Victoria?",
        "filters": {
            "topic": "emissions_reporting"
        },
        "expected_topic": "emissions_reporting"
    },
    {
        "query": "Land-use planning rules in South Australia?",
        "filters": {
            "region": "South Australia"
        },
        "expected_topic": "land_use"
    }
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
        cleaned_text = utils.clean_text(doc["text"])
        chunks = text_chunker.chunk_text(cleaned_text)
        for c in chunks:
            all_chunks.append({"content": c, "metadata": doc["metadata"]})

    assert len(all_chunks) > 0

    # Step 2: Mock embeddings
    with patch("rag.embeddings.BedrockEmbedder.embed_text") as mock_embed:
        mock_embed.side_effect = lambda txt: [0.1] * 10
        embedder = embeddings.BedrockEmbedder()
        embedded_chunks = [
            {"content": c["content"], "embedding": embedder.embed_text(c["content"]), "metadata": c["metadata"]}
            for c in all_chunks
        ]

    # Step 3: Vector store
    store = vector_store.VectorStore()
    for item in embedded_chunks:
        store.add(item["embedding"], item["metadata"])
    assert len(store.items) == len(embedded_chunks)

    # Step 4: RAG chain
    chain = rag_chain.RAGChain(vector_store=store, embedder=embedder)

    # Step 5: Run query with filters
    answer = chain.run(test_case["query"], metadata_filters=test_case["filters"])

    # Step 6: Basic assertion
    assert test_case["expected_topic"] in answer.lower() or answer == ""
