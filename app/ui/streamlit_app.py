
# pip install streamlit streamlit-folium folium geopandas

import streamlit as st
from streamlit_folium import st_folium
import folium
import json
import geopandas as gpd

# Load GeoJSON of Australian LGAs (ABS or other source)
@st.cache_data
def load_lga_data():
    gdf = gpd.read_file("australia_lga.geojson")  # Must include 'LGA_NAME' or similar
    return gdf

gdf = load_lga_data()

st.title("🗺️ GreenGovRAG - LGA Policy Explorer")

# Center on South Australia for default zoom
m = folium.Map(location=[-34.9285, 138.6007], zoom_start=5)

# Define callback function for highlighting
def highlight_function(feature):
    return {
        'fillColor': '#ffff00',
        'color': 'blue',
        'weight': 2,
        'fillOpacity': 0.2
    }

# Add GeoJSON layer with tooltip for LGA names
folium.GeoJson(
    gdf,
    name="LGAs",
    tooltip=folium.GeoJsonTooltip(fields=["LGA_NAME"]),
    highlight_function=highlight_function
).add_to(m)

# Render Folium map in Streamlit
st_map = st_folium(m, width=700, height=500)

# Capture click coordinates
if st_map and st_map["last_clicked"]:
    lat = st_map["last_clicked"]["lat"]
    lon = st_map["last_clicked"]["lng"]
    st.write(f"📍 Clicked Coordinates: {lat:.4f}, {lon:.4f}")

    # Find LGA containing clicked point
    point = gpd.GeoSeries(gpd.points_from_xy([lon], [lat]), crs=gdf.crs)
    match = gdf[gdf.contains(point[0])]

    if not match.empty:
        lga_name = match.iloc[0]["LGA_NAME"]
        st.success(f"✅ Selected LGA: **{lga_name}**")

        # Placeholder: Send to RAG query
        st.button("🔍 Query Environmental Rules", key="query")
    else:
        st.warning("No LGA found at this point.")
