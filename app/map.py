# Folium + GeoJSON integration
import folium
import streamlit as st
import json

def load_geojson(path):
    with open(path, "r") as f:
        return json.load(f)

def render_map(selected_lga=None):
    geojson = load_geojson("../data/geo/aus_lga.geojson")
    m = folium.Map(location=[-25.0, 135.0], zoom_start=4)

    def style_function(feature):
        if selected_lga and feature['properties']['LGA_NAME'] == selected_lga:
            return {'fillColor': '#ff7800', 'color': 'black', 'weight': 2, 'fillOpacity': 0.7}
        else:
            return {'fillColor': '#grey', 'color': 'black', 'weight': 1, 'fillOpacity': 0.3}

    folium.GeoJson(
        geojson,
        name="LGAs",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=["LGA_NAME"])
    ).add_to(m)

    return m

def folium_static(m):
    import streamlit.components.v1 as components
    components.html(m._repr_html_(), height=500)
