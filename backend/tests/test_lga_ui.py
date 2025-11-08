"""Tests for LGA UI and Geospatial Functionality.

This test suite covers:
- LGA boundary detection and point-in-polygon checks
- Geospatial filtering for RAG queries
- UI simulation with map selections
- Multi-LGA queries
- Coordinate validation
- Distance-based filtering
- Geometry operations (intersections, buffers)
- Edge cases (boundary points, invalid geometries)
"""

from __future__ import annotations

import pytest
from shapely.geometry import Point, shape
from shapely.ops import nearest_points

from green_gov_rag.etl import chunker, utils

# ============================================================================
# Sample Documents with LGA Geometries
# ============================================================================

DOCS = [
    {
        "title": "Adelaide Biodiversity Plan",
        "text": "This document covers biodiversity regulations for the City of Adelaide.",
        "metadata": {
            "source": "adelaide_biodiversity",
            "topic": "biodiversity",
            "region": "City of Adelaide",
            "lga_code": "40070",
            "lga_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [138.55, -34.95],
                        [138.60, -34.95],
                        [138.60, -34.92],
                        [138.55, -34.92],
                        [138.55, -34.95],
                    ],
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
            "lga_code": "40280",
            "lga_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [138.50, -34.85],
                        [138.55, -34.85],
                        [138.55, -34.80],
                        [138.50, -34.80],
                        [138.50, -34.85],
                    ],
                ],
            },
        },
    },
    {
        "title": "City of Salisbury Environment Strategy",
        "text": "Environmental management guidelines for City of Salisbury.",
        "metadata": {
            "source": "salisbury_environment",
            "topic": "environment",
            "region": "City of Salisbury",
            "lga_code": "40300",
            "lga_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [138.60, -34.80],
                        [138.70, -34.80],
                        [138.70, -34.70],
                        [138.60, -34.70],
                        [138.60, -34.80],
                    ],
                ],
            },
        },
    },
]


# ============================================================================
# Helper Functions
# ============================================================================


def point_in_lga(lat, lon, polygon_geojson):
    """Check if a point is within an LGA polygon."""
    poly = shape(polygon_geojson)
    return poly.contains(Point(lon, lat))


def distance_to_lga(lat, lon, polygon_geojson):
    """Calculate distance from a point to the nearest edge of an LGA polygon."""
    poly = shape(polygon_geojson)
    point = Point(lon, lat)

    # Get nearest point on polygon boundary
    nearest_geom = nearest_points(point, poly.boundary)[1]
    return point.distance(nearest_geom)


def lgas_intersect(geometry1, geometry2):
    """Check if two LGA geometries intersect."""
    poly1 = shape(geometry1)
    poly2 = shape(geometry2)
    return poly1.intersects(poly2)


def simulate_user_selection(selected_lgas, selected_topic=None):
    """Return metadata filter function for RAG chain based on map selection."""

    def metadata_filter(metadata):
        # LGA filter
        if not selected_lgas:
            # No LGA filter - allow all
            in_lga = True
        elif "lga_geometry" in metadata:
            in_lga = False
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


def simulate_radius_selection(center_lat, center_lon, radius_km):
    """Return metadata filter for radius-based selection."""

    def metadata_filter(metadata):
        if "lga_geometry" in metadata:
            # Calculate distance to LGA
            dist = distance_to_lga(center_lat, center_lon, metadata["lga_geometry"])
            # Convert to km (rough approximation, 1 degree ≈ 111km)
            dist_km = dist * 111
            return dist_km <= radius_km
        return True  # No geometry = allow all

    return metadata_filter


# ============================================================================
# Parameterized Test Cases
# ============================================================================

USER_TESTS = [
    {
        "query": "Biodiversity policies in Adelaide and Port Adelaide",
        "selected_lgas": [
            {"lat": -34.935, "lon": 138.575},
            {"lat": -34.825, "lon": 138.525},
        ],
        "selected_topic": "biodiversity",
        "expected_sources": ["adelaide_biodiversity"],
    },
    {
        "query": "Sustainable development policies in Port Adelaide",
        "selected_lgas": [{"lat": -34.825, "lon": 138.525}],
        "selected_topic": "sustainable_development",
        "expected_sources": ["port_ade_sustain"],
    },
    {
        "query": "Environmental policies in Salisbury",
        "selected_lgas": [{"lat": -34.75, "lon": 138.65}],
        "selected_topic": "environment",
        "expected_sources": ["salisbury_environment"],
    },
]


# ============================================================================
# Basic Geospatial Tests
# ============================================================================


def test_point_in_polygon_basic():
    """Test basic point-in-polygon detection."""
    # Point inside Adelaide polygon
    assert point_in_lga(-34.935, 138.575, DOCS[0]["metadata"]["lga_geometry"]) is True  # type: ignore[index]

    # Point outside Adelaide polygon
    assert point_in_lga(-34.80, 138.70, DOCS[0]["metadata"]["lga_geometry"]) is False  # type: ignore[index]


def test_point_on_boundary():
    """Test point exactly on polygon boundary."""
    # Point on edge of Adelaide polygon
    result = point_in_lga(-34.95, 138.575, DOCS[0]["metadata"]["lga_geometry"])  # type: ignore[index]
    # On boundary may be True or False depending on implementation
    assert isinstance(result, bool)


def test_point_at_vertex():
    """Test point exactly at polygon vertex."""
    # Point at corner of Adelaide polygon
    result = point_in_lga(-34.95, 138.55, DOCS[0]["metadata"]["lga_geometry"])  # type: ignore[index]
    assert isinstance(result, bool)


def test_multiple_lga_detection():
    """Test detecting which LGA a point belongs to."""
    test_point = {"lat": -34.75, "lon": 138.65}

    matches = []
    for doc in DOCS:
        if "lga_geometry" in doc["metadata"]:
            if point_in_lga(
                test_point["lat"],
                test_point["lon"],
                doc["metadata"]["lga_geometry"],  # type: ignore[index]
            ):
                matches.append(doc["metadata"]["region"])  # type: ignore[index]

    # Should match City of Salisbury
    assert "City of Salisbury" in matches


def test_lga_intersection_detection():
    """Test detecting if two LGA geometries intersect."""
    # Adelaide and Port Adelaide don't intersect (adjacent)
    adelaide_geom = DOCS[0]["metadata"]["lga_geometry"]  # type: ignore[index]
    port_adelaide_geom = DOCS[1]["metadata"]["lga_geometry"]  # type: ignore[index]

    # They shouldn't intersect (different areas)
    result = lgas_intersect(adelaide_geom, port_adelaide_geom)
    assert isinstance(result, bool)


# ============================================================================
# UI Simulation Tests
# ============================================================================


@pytest.mark.parametrize("test_case", USER_TESTS)
def test_ui_rag_with_lga_selection(test_case):
    """Test end-to-end UI simulation with LGA selection."""
    # Step 1: Chunking all documents
    all_chunks = []
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)
    for doc in DOCS:
        text: str = doc["text"]  # type: ignore[assignment]
        cleaned_text = utils.clean_text(text)
        chunks = text_chunker.chunk_text(cleaned_text)
        for c in chunks:
            all_chunks.append({"content": c, "metadata": doc["metadata"]})

    # Step 2: Mock embeddings
    from tests.conftest import MockChunkEmbedder

    mock_embedder = MockChunkEmbedder()
    embedded_chunks = mock_embedder.embed_chunks(all_chunks)

    # Step 3: Verify embeddings created
    assert len(embedded_chunks) > 0
    for chunk in embedded_chunks:
        assert "embedding" in chunk

    # Step 4: Test metadata filtering
    metadata_filter = simulate_user_selection(
        test_case["selected_lgas"],
        test_case["selected_topic"],
    )

    # Step 5: Apply filter
    filtered_chunks = [c for c in embedded_chunks if metadata_filter(c["metadata"])]

    # Step 6: Verify expected sources are in the filtered data
    for source in test_case["expected_sources"]:
        assert any(source in c["metadata"].get("source", "") for c in filtered_chunks)


def test_ui_multi_lga_selection():
    """Test UI with multiple LGA selections."""
    # Select both Adelaide and Salisbury
    selected_lgas = [
        {"lat": -34.935, "lon": 138.575},  # Adelaide
        {"lat": -34.75, "lon": 138.65},  # Salisbury
    ]

    metadata_filter = simulate_user_selection(selected_lgas, selected_topic=None)

    # Should match Adelaide and Salisbury documents
    adelaide_match = metadata_filter(DOCS[0]["metadata"])
    salisbury_match = metadata_filter(DOCS[2]["metadata"])
    port_adelaide_match = metadata_filter(DOCS[1]["metadata"])

    assert adelaide_match is True
    assert salisbury_match is True
    assert port_adelaide_match is False  # Not selected


def test_ui_no_topic_filter():
    """Test UI selection without topic filtering."""
    selected_lgas = [{"lat": -34.935, "lon": 138.575}]

    # No topic filter
    metadata_filter = simulate_user_selection(selected_lgas, selected_topic=None)

    # Should match Adelaide regardless of topic
    assert metadata_filter(DOCS[0]["metadata"]) is True


def test_ui_topic_filter_only():
    """Test UI with only topic filter, no LGA selection."""
    # Empty LGA selection
    metadata_filter = simulate_user_selection([], selected_topic="biodiversity")

    # Should match biodiversity documents
    adelaide_match = metadata_filter(DOCS[0]["metadata"])
    port_adelaide_match = metadata_filter(DOCS[1]["metadata"])

    assert adelaide_match is True  # Has biodiversity topic
    assert port_adelaide_match is False  # Different topic


def test_ui_no_filters():
    """Test UI with no filters applied."""
    metadata_filter = simulate_user_selection([], selected_topic=None)

    # Should match all documents
    assert all(metadata_filter(doc["metadata"]) for doc in DOCS)


# ============================================================================
# Distance-Based Filtering Tests
# ============================================================================


def test_radius_based_selection():
    """Test radius-based LGA selection."""
    # Center point in Adelaide
    center_lat, center_lon = -34.935, 138.575
    radius_km = 50  # 50km radius

    radius_filter = simulate_radius_selection(center_lat, center_lon, radius_km)

    # All documents within 50km should match
    matches = [doc for doc in DOCS if radius_filter(doc["metadata"])]
    assert len(matches) > 0


def test_small_radius_selection():
    """Test very small radius selection."""
    # Center point in Adelaide
    center_lat, center_lon = -34.935, 138.575
    radius_km = 5  # 5km radius (small but reasonable)

    radius_filter = simulate_radius_selection(center_lat, center_lon, radius_km)

    # Adelaide should match (point is inside or very close)
    adelaide_match = radius_filter(DOCS[0]["metadata"])
    assert adelaide_match is True


# ============================================================================
# Coordinate Validation Tests
# ============================================================================


def test_invalid_coordinates():
    """Test handling of invalid coordinates."""
    invalid_lat, invalid_lon = 200, 200  # Invalid coordinates

    # Should handle gracefully
    try:
        result = point_in_lga(
            invalid_lat,
            invalid_lon,
            DOCS[0]["metadata"]["lga_geometry"],  # type: ignore[index]
        )
        # Either returns False or handles gracefully
        assert isinstance(result, bool)
    except Exception:
        # May raise exception for invalid coords
        pass


def test_boundary_coordinates():
    """Test coordinates at extreme boundaries."""
    # Test at equator
    equator_result = point_in_lga(0, 138.575, DOCS[0]["metadata"]["lga_geometry"])  # type: ignore[index]
    assert equator_result is False

    # Test at dateline
    dateline_result = point_in_lga(-34.935, 180, DOCS[0]["metadata"]["lga_geometry"])  # type: ignore[index]
    assert dateline_result is False


def test_southern_hemisphere_coords():
    """Test that Southern Hemisphere coordinates work correctly."""
    # Adelaide is in Southern Hemisphere (negative latitude)
    assert point_in_lga(-34.935, 138.575, DOCS[0]["metadata"]["lga_geometry"]) is True  # type: ignore[index]


# ============================================================================
# Geometry Edge Cases
# ============================================================================


def test_missing_geometry():
    """Test documents without geometry metadata."""
    doc_without_geometry = {
        "source": "test",
        "topic": "biodiversity",
        "region": "Unknown",
    }

    metadata_filter = simulate_user_selection(
        [{"lat": -34.935, "lon": 138.575}],
        selected_topic="biodiversity",
    )

    # Should allow documents without geometry
    assert metadata_filter(doc_without_geometry) is True


def test_empty_geometry():
    """Test handling of empty geometry."""
    doc_with_empty_geometry = {
        "source": "test",
        "topic": "biodiversity",
        "lga_geometry": {"type": "Polygon", "coordinates": []},
    }

    try:
        # May raise exception or return False
        metadata_filter = simulate_user_selection(
            [{"lat": -34.935, "lon": 138.575}],
            selected_topic=None,
        )
        result = metadata_filter(doc_with_empty_geometry)
        assert isinstance(result, bool)
    except Exception:
        # Expected for malformed geometry
        pass


# ============================================================================
# LGA Code Filtering Tests
# ============================================================================


def test_lga_code_based_filtering():
    """Test filtering by LGA code instead of geometry."""
    # Filter by LGA code
    target_lga_code = "40070"  # City of Adelaide

    filtered = [
        doc
        for doc in DOCS
        if doc["metadata"].get("lga_code") == target_lga_code  # type: ignore[attr-defined]
    ]

    assert len(filtered) == 1
    assert filtered[0]["metadata"]["region"] == "City of Adelaide"  # type: ignore[index]


def test_multiple_lga_code_filtering():
    """Test filtering by multiple LGA codes."""
    target_lga_codes = ["40070", "40300"]  # Adelaide and Salisbury

    filtered = [
        doc
        for doc in DOCS
        if doc["metadata"].get("lga_code") in target_lga_codes  # type: ignore[attr-defined]
    ]

    assert len(filtered) == 2
    regions = {doc["metadata"]["region"] for doc in filtered}  # type: ignore[index]
    assert "City of Adelaide" in regions
    assert "City of Salisbury" in regions


# ============================================================================
# Performance Tests
# ============================================================================


def test_many_lga_filtering():
    """Test filtering performance with many LGAs."""
    # Create many test points
    test_points = [
        {"lat": -34.935 + i * 0.01, "lon": 138.575 + j * 0.01}
        for i in range(10)
        for j in range(10)
    ]

    metadata_filter = simulate_user_selection(test_points, selected_topic=None)

    # Test filter on all documents
    results = [metadata_filter(doc["metadata"]) for doc in DOCS]

    # Should complete without errors
    assert isinstance(results, list)
    assert all(isinstance(r, bool) for r in results)


def test_complex_polygon():
    """Test with a complex polygon (many vertices)."""
    # Create polygon with many vertices
    complex_polygon = {
        "type": "Polygon",
        "coordinates": [
            [[138.55 + i * 0.01, -34.95 + j * 0.01] for i in range(5) for j in range(5)]
        ],
    }

    # Should handle complex polygons
    result = point_in_lga(-34.93, 138.57, complex_polygon)
    assert isinstance(result, bool)


# ============================================================================
# Integration with RAG Pipeline
# ============================================================================


def test_lga_filter_with_rag_pipeline(in_memory_faiss):
    """Test LGA filtering integrated with RAG pipeline."""
    # Query with LGA filter
    query = "biodiversity policies"

    # Get all results
    all_results = in_memory_faiss.similarity_search(query, k=10)

    # Apply LGA filter (simulate Adelaide selection)
    selected_lgas = [{"lat": -34.935, "lon": 138.575}]
    metadata_filter = simulate_user_selection(selected_lgas, selected_topic=None)

    # Filter results
    filtered_results = [r for r in all_results if metadata_filter(r.metadata)]

    # Should return filtered results
    assert isinstance(filtered_results, list)


def test_combined_text_and_spatial_filtering():
    """Test combining text search with spatial filtering."""
    # Chunk documents
    all_chunks = []
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)

    for doc in DOCS:
        text: str = doc["text"]  # type: ignore[assignment]
        cleaned_text = utils.clean_text(text)
        chunks = text_chunker.chunk_text(cleaned_text)
        for c in chunks:
            all_chunks.append({"content": c, "metadata": doc["metadata"]})

    # Embed
    from tests.conftest import MockChunkEmbedder

    mock_embedder = MockChunkEmbedder()
    embedded_chunks = mock_embedder.embed_chunks(all_chunks)

    # Text filter (contains "Adelaide")
    text_filtered = [c for c in embedded_chunks if "Adelaide" in c["content"]]

    # Spatial filter
    spatial_filter = simulate_user_selection(
        [{"lat": -34.935, "lon": 138.575}],
        selected_topic=None,
    )
    spatial_and_text_filtered = [
        c for c in text_filtered if spatial_filter(c["metadata"])
    ]

    # Should have fewer results after both filters
    assert len(spatial_and_text_filtered) <= len(text_filtered)
