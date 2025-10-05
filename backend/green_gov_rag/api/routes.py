"""API routes for GreenGovRAG."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from green_gov_rag import __version__
from green_gov_rag.api.schemas import (
    AnalyticsStats,
    DocumentListResponse,
    DocumentResponse,
    QueryRequest,
    QueryResponse,
)
from green_gov_rag.api.services import (
    AnalyticsService,
    DocumentService,
    QueryService,
)

router = APIRouter()

# Initialize services
query_service = QueryService()
document_service = DocumentService()
analytics_service = AnalyticsService()


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "GreenGovRAG API", "version": __version__}


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest) -> QueryResponse:
    """Execute RAG query with filters.

    Args:
        request: Query request with filters

    Returns:
        QueryResponse: Answer with source docume
    """
    try:
        return query_service.execute_query(
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


@router.get("/analytics/stats", response_model=AnalyticsStats)
async def get_analytics() -> AnalyticsStats:
    """Get analytics statistics.

    Returns:
        AnalyticsStats: Overall statistics and distributions
    """
    return analytics_service.get_stats()


@router.get("/map/lgas")
async def get_lga_geojson():
    """Get LGA boundaries as GeoJSON.

    Returns:
        dict: GeoJSON FeatureCollection
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
            return json.load(f)

    # Return mock GeoJSON for development
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Sydney", "LGA_NAME": "Sydney", "state": "NSW"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [151.1, -33.8],
                            [151.3, -33.8],
                            [151.3, -34.0],
                            [151.1, -34.0],
                            [151.1, -33.8],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Melbourne",
                    "LGA_NAME": "Melbourne",
                    "state": "VIC",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [144.8, -37.7],
                            [145.0, -37.7],
                            [145.0, -37.9],
                            [144.8, -37.9],
                            [144.8, -37.7],
                        ]
                    ],
                },
            },
        ],
    }
