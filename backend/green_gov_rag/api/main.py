"""FastAPI application main module."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from green_gov_rag import __version__
from green_gov_rag.api.admin import router as admin_router
from green_gov_rag.api.routes import limiter
from green_gov_rag.api.routes import router as api_router
from green_gov_rag.api.schemas import RootResponse
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

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(admin_router, prefix="/api")


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    """Root endpoint."""
    return RootResponse(
        service="GreenGovRAG API",
        version=__version__,
        docs="/docs",
        admin="/api/admin/dashboard",
        health="/api/health",
    )
