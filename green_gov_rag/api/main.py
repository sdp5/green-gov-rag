"""FastAPI application main module."""

# API endpoints

from api.routes import router as api_router
from fastapi import FastAPI

app = FastAPI(
    title="GreenGovRAG API",
    description="API for querying environmental regulations with RAG + geospatial filters",
    version="0.1",
)

app.include_router(api_router)
