"""Tests for UI components."""

from unittest.mock import MagicMock, patch

import folium
import pytest
from app import config, map, ui


# -----------------------------
# Config checks
# -----------------------------
def test_config_constants():
    assert hasattr(config, "MAP_CENTER")
    assert isinstance(config.MAP_CENTER, list)
    assert len(config.MAP_CENTER) == 2
    assert hasattr(config, "MAP_ZOOM_START")
    assert isinstance(config.MAP_ZOOM_START, int)


# -----------------------------
# Map functions
# -----------------------------
def test_create_map_default():
    m = map.create_map()
    assert isinstance(m, folium.Map)
    # Center coordinates should match config
    assert m.location == config.MAP_CENTER
    assert m.zoom_start == config.MAP_ZOOM_START  # type: ignore[attr-defined]


def test_add_geojson_layer(tmp_path):
    # Create a dummy GeoJSON
    geojson_file = tmp_path / "sample.geojson"
    geojson_file.write_text('{"type": "FeatureCollection", "features": []}')
    m = folium.Map(location=config.MAP_CENTER, zoom_start=config.MAP_ZOOM_START)
    m = map.add_geojson_layer(m, str(geojson_file))
    assert isinstance(m, folium.Map)


# -----------------------------
# Query tab / RAG integration
# -----------------------------
def test_run_query_returns_string():
    # Patch RAG function
    with patch("app.ui.rag_chain.RAGChain.run") as mock_rag:
        mock_rag.return_value = "Test answer"
        answer = ui.run_query("What is biodiversity?")
        assert answer == "Test answer"


def test_run_query_with_metadata_filters():
    with patch("app.ui.rag_chain.RAGChain.run") as mock_rag:
        mock_rag.return_value = "Filtered answer"
        filters = {"region": "NSW"}
        answer = ui.run_query("Emissions report", metadata_filters=filters)
        mock_rag.assert_called_with("Emissions report", metadata_filters=filters)
        assert answer == "Filtered answer"


# -----------------------------
# Full dashboard / tab simulation
# -----------------------------
@patch("app.ui.run_query", return_value="Dummy answer")
def test_main_dashboard(mock_query):
    # Patch Streamlit functions to prevent actual UI rendering
    with patch("streamlit.sidebar.selectbox", return_value="Query"):
        with patch("streamlit.button", return_value=True):
            # Check that main runs without exception
            try:
                ui.main()
            except Exception as e:
                pytest.fail(f"Streamlit main raised an exception: {e}")
    mock_query.assert_called()


# -----------------------------
# Tab switching simulation
# -----------------------------
@patch("app.ui.run_query", return_value="Dummy answer")
def test_tabs_interaction(mock_query):
    # Simulate selecting Map tab
    with patch("streamlit.sidebar.selectbox", return_value="Map"):
        with patch("streamlit.map", MagicMock()):
            try:
                ui.main()
            except Exception as e:
                pytest.fail(f"Map tab raised exception: {e}")

    # Simulate selecting Analytics tab
    with patch("streamlit.sidebar.selectbox", return_value="Analytics"):
        try:
            ui.main()
        except Exception as e:
            pytest.fail(f"Analytics tab raised exception: {e}")

    # Simulate selecting Sources tab
    with patch("streamlit.sidebar.selectbox", return_value="Sources"):
        try:
            ui.main()
        except Exception as e:
            pytest.fail(f"Sources tab raised exception: {e}")
