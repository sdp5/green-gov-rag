"""UI Application configuration.

Now uses centralized settings from green_gov_rag.config
"""

from green_gov_rag.config import settings

# Application title and description
APP_TITLE = "GreenGovRAG 🌿"
APP_DESCRIPTION = "AI Assistant for Australian Environmental & Planning Regulations"

# Map configuration
MAP_CENTER = [-25.0, 133.0]  # Australia center
MAP_ZOOM_START = 4
MAP_TILE = "OpenStreetMap"

# LGA visualization
LGA_GEOJSON_PATH = "data/geo/abs_lga_boundaries.geojson"
LGA_DEFAULT_COLOR = "#3388ff"
LGA_SELECTED_COLOR = "#ff7800"
LGA_DEFAULT_OPACITY = 0.4
LGA_SELECTED_OPACITY = 0.7

# Topic options for filtering
TOPIC_OPTIONS = [
    "biodiversity",
    "emissions",
    "planning",
    "water_management",
    "vegetation_clearance",
    "sustainable_development",
]

# Model configuration (from centralized settings)
EMBEDDING_MODEL = settings.embedding_model
LLM_MODEL = settings.llm_model
OPENAI_API_KEY = settings.openai_api_key
