import os

# ----------------------------
# Application Settings
# ----------------------------
APP_TITLE = "GreenGovRAG: Environmental Policy Assistant"
APP_DESCRIPTION = "GenAI-powered policy query system with geospatial support (LGA, state, federal)."

# ----------------------------
# Paths
# ----------------------------
DATA_DIR = "data"
RAW_DOCS_DIR = f"{DATA_DIR}/raw"
PROCESSED_DOCS_DIR = f"{DATA_DIR}/processed"
GEO_DIR = f"{DATA_DIR}/geo"
LGA_GEOJSON_PATH = f"{GEO_DIR}/abs_lga_boundaries.geojson"

# ----------------------------
# Map Settings
# ----------------------------
MAP_CENTER = [-25.0, 133.0]  # Australia central coordinates
MAP_ZOOM_START = 4
MAP_TILE = "OpenStreetMap"
MAP_WIDTH = 800
MAP_HEIGHT = 600

# Folium colors
LGA_DEFAULT_COLOR = "blue"
LGA_SELECTED_COLOR = "green"
LGA_DEFAULT_OPACITY = 0.1
LGA_SELECTED_OPACITY = 0.5

# ----------------------------
# RAG / Embeddings Settings
# ----------------------------
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "huggingface/sentence-transformers/all-MiniLM-L6-v2")
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/text-davinci-003")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# ----------------------------
# UI Defaults
# ----------------------------
DEFAULT_REGION_FILTER = "All"
TOPIC_OPTIONS = [
    "biodiversity",
    "emissions_reporting",
    "planning",
    "standards",
    "land_use",
    "sustainable_development"
]
