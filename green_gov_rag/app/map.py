import json

import folium
import geopandas as gpd
import streamlit as st
from app.config import (
    LGA_DEFAULT_COLOR,
    LGA_DEFAULT_OPACITY,
    LGA_GEOJSON_PATH,
    LGA_SELECTED_COLOR,
    LGA_SELECTED_OPACITY,
    MAP_CENTER,
    MAP_TILE,
    MAP_ZOOM_START,
)
from streamlit_folium import st_folium


@st.cache_data
def load_geojson(path=LGA_GEOJSON_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_map(selected_lgas=None):
    """
    Create a Folium map of Australia with LGA boundaries.
    :param selected_lgas: list of selected LGA names
    """
    selected_lgas = selected_lgas or []

    m = folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM_START, tiles=MAP_TILE)

    geojson_data = load_geojson()

    def style_function(feature):
        name = feature["properties"].get("LGA_NAME") or feature["properties"].get("NAME")
        if name in selected_lgas:
            return {
                "fillColor": LGA_SELECTED_COLOR,
                "color": LGA_SELECTED_COLOR,
                "weight": 2,
                "fillOpacity": LGA_SELECTED_OPACITY,
            }
        else:
            return {
                "fillColor": LGA_DEFAULT_COLOR,
                "color": LGA_DEFAULT_COLOR,
                "weight": 1,
                "fillOpacity": LGA_DEFAULT_OPACITY,
            }

    folium.GeoJson(
        geojson_data,
        name="LGAs",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=["LGA_NAME"], aliases=["LGA:"], labels=True),
        highlight_function=lambda x: {"weight": 3, "color": "yellow"},
    ).add_to(m)

    return m
