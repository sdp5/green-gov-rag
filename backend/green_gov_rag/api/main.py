"""FastAPI application main module."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from green_gov_rag import __version__
from green_gov_rag.api.routes import router as api_router
from green_gov_rag.config import settings
from green_gov_rag.models.base import init_db

# Create FastAPI app
app = FastAPI(
    title="GreenGovRAG API",
    description="API for querying environmental regulations with RAG + geospatial filters",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "GreenGovRAG API",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/health",
    }
