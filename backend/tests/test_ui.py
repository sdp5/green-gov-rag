"""Tests for UI components."""

from unittest.mock import MagicMock, patch

import folium

from green_gov_rag.app import config, map, ui


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
    # Mock the load_geojson to avoid file dependency
    with patch("green_gov_rag.app.map.load_geojson") as mock_load:
        mock_load.return_value = {"type": "FeatureCollection", "features": []}
        m = map.create_map()
        assert isinstance(m, folium.Map)
        # Center coordinates should match config
        assert m.location == config.MAP_CENTER


def test_add_geojson_layer(tmp_path):
    # Create a dummy GeoJSON
    geojson_data = {"type": "FeatureCollection", "features": []}
    m = folium.Map(location=config.MAP_CENTER, zoom_start=config.MAP_ZOOM_START)
    m = map.add_geojson_layer(m, geojson_data)
    assert isinstance(m, folium.Map)


# -----------------------------
# Query tab / RAG integration
# -----------------------------
def test_run_query_returns_string():
    # Patch RAG agent query method
    with patch("green_gov_rag.app.ui.get_rag_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.query.return_value = ("Test answer", [])
        mock_get_agent.return_value = mock_agent
        answer = ui.run_query("What is biodiversity?")
        assert answer == "Test answer"


def test_run_query_with_metadata_filters():
    with patch("green_gov_rag.app.ui.get_rag_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.query.return_value = ("Filtered answer", [])
        mock_get_agent.return_value = mock_agent
        filters = {"region": "NSW"}
        answer = ui.run_query("Emissions report", metadata_filters=filters)
        mock_agent.query.assert_called_with(
            "Emissions report",
            metadata_filters=filters,
        )
        assert answer == "Filtered answer"


# -----------------------------
# Full dashboard / tab simulation
# -----------------------------
@patch("green_gov_rag.app.ui.render_ui")
def test_main_dashboard(mock_render):
    # Check that main calls render_ui
    ui.main()
    mock_render.assert_called_once()


# -----------------------------
# Tab switching simulation
# -----------------------------
@patch("green_gov_rag.app.ui.render_ui")
def test_tabs_interaction(mock_render):
    # Test that tabs can be rendered
    ui.main()
    mock_render.assert_called()
