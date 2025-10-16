"""API routes for GreenGovRAG."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from green_gov_rag import __version__
from green_gov_rag.api.schemas import (
    AnalyticsStats,
    DocumentListResponse,
    DocumentResponse,
    FeedbackRequest,
    FeedbackResponse,
    GeoJSONFeature,
    GeoJSONGeometry,
    GeoJSONResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from green_gov_rag.api.services import (
    AnalyticsService,
    DocumentService,
    QueryService,
)

router = APIRouter()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize services
query_service = QueryService()
document_service = DocumentService()
analytics_service = AnalyticsService()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", service="GreenGovRAG API", version=__version__)


@router.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute")
async def query_rag(http_request: Request, request: QueryRequest) -> QueryResponse:
    """Execute RAG query with filters.

    Args:
        http_request: HTTP request for rate limiting
        request: Query request with filters

    Returns:
        QueryResponse: Answer with source docume
    """
    try:
        return await query_service.execute_query(
            query=request.query,
            region=request.region,
            jurisdiction=request.jurisdiction,
            topics=request.topics,
            max_sources=request.max_sources,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    region: Optional[str] = Query(None, description="Filter by region"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> DocumentListResponse:
    """List documents with optional filters.

    Args:
        jurisdiction: Filter by jurisdiction
        topic: Filter by topic
        region: Filter by region
        status: Filter by status
        limit: Max results
        offset: Pagination offset

    Returns:
        DocumentListResponse: Paginated document list
    """
    return document_service.get_documents(
        jurisdiction=jurisdiction,
        topic=topic,
        region=region,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str) -> DocumentResponse:
    """Get document by ID.

    Args:
        document_id: Document ID

    Returns:
        DocumentResponse: Document details

    Raises:
        HTTPException: If document not found
    """
    doc = document_service.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/query/{query_id}/feedback", response_model=FeedbackResponse)
@limiter.limit("5/minute")
async def submit_feedback(
    http_request: Request, query_id: int, request: FeedbackRequest
) -> FeedbackResponse:
    """Submit feedback for a query.

    Args:
        query_id: Query history ID
        request: Feedback request with rating and optional text

    Returns:
        FeedbackResponse: Feedback submission confirmation

    Raises:
        HTTPException: If query not found or feedback submission fails
    """
    try:
        success = await query_service.submit_feedback(
            query_id=query_id,
            rating=request.rating,
            feedback_text=request.feedback_text,
        )
        if not success:
            raise HTTPException(status_code=404, detail="Query not found")

        return FeedbackResponse(
            success=True, message="Feedback submitted successfully", query_id=query_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/analytics/stats", response_model=AnalyticsStats)
async def get_analytics() -> AnalyticsStats:
    """Get analytics statistics.

    Returns:
        AnalyticsStats: Overall statistics and distributions
    """
    return analytics_service.get_stats()


@router.get("/map/lgas", response_model=GeoJSONResponse)
async def get_lga_geojson() -> GeoJSONResponse:
    """Get LGA boundaries as GeoJSON.

    Returns:
        GeoJSONResponse: GeoJSON FeatureCollection
    """
    # Use absolute path relative to project root
    # Go up from backend/green_gov_rag/api/ to project root
    api_dir = Path(__file__).parent
    project_root = api_dir.parent.parent.parent
    # Data obtained from:
    # - Australian Bureau of Statistics (ABS): https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files
    # - data.gov.au: https://data.gov.au/
    geojson_path = project_root / "data" / "geo" / "aus_lga.geojson"

    # Check if file exists
    if geojson_path.exists():
        import json

        with open(geojson_path) as f:
            data = json.load(f)
            return GeoJSONResponse(**data)

    # Return mock GeoJSON for development
    return GeoJSONResponse(
        type="FeatureCollection",
        features=[
            GeoJSONFeature(
                type="Feature",
                properties={"name": "Sydney", "LGA_NAME": "Sydney", "state": "NSW"},
                geometry=GeoJSONGeometry(
                    type="Polygon",
                    coordinates=[
                        [
                            [151.1, -33.8],
                            [151.3, -33.8],
                            [151.3, -34.0],
                            [151.1, -34.0],
                            [151.1, -33.8],
                        ]
                    ],
                ),
            ),
            GeoJSONFeature(
                type="Feature",
                properties={
                    "name": "Melbourne",
                    "LGA_NAME": "Melbourne",
                    "state": "VIC",
                },
                geometry=GeoJSONGeometry(
                    type="Polygon",
                    coordinates=[
                        [
                            [144.8, -37.7],
                            [145.0, -37.7],
                            [145.0, -37.9],
                            [144.8, -37.9],
                            [144.8, -37.7],
                        ]
                    ],
                ),
            ),
        ],
    )
