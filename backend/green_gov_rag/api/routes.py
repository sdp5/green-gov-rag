"""API routes for GreenGovRAG."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi import Query as QueryParam
from slowapi import Limiter
from slowapi.util import get_remote_address

from green_gov_rag import __version__
from green_gov_rag.api.schemas import (
    AnalyticsStats,
    CoverageInfo,
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
    VectorStoreStatus,
)
from green_gov_rag.api.services import (
    AnalyticsService,
    CoverageService,
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
coverage_service = CoverageService()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint with vector store status."""
    # Check vector store health
    vector_store_status = _check_vector_store_health()

    # Overall status is degraded if vector store has issues
    overall_status = "ok" if vector_store_status.status == "ok" else "degraded"

    return HealthResponse(
        status=overall_status,
        service="GreenGovRAG API",
        version=__version__,
        vector_store=vector_store_status,
    )


def _check_vector_store_health() -> VectorStoreStatus:
    """Check vector store health and return status.

    Returns:
        VectorStoreStatus with current status
    """
    try:
        # Try to get document count from query service's RAG agent
        if hasattr(query_service, "rag_agent"):
            doc_count = query_service.rag_agent._get_vector_store_count()

            if doc_count == 0:
                return VectorStoreStatus(
                    status="empty",
                    document_count=0,
                    error="Vector store contains no documents",
                    remediation=(
                        "Run document ingestion:\n"
                        "  python -m green_gov_rag.etl.ingest_documents\n"
                        "Or with Docker:\n"
                        "  docker-compose run --rm backend python -m green_gov_rag.etl.ingest_documents"
                    ),
                )

            return VectorStoreStatus(status="ok", document_count=doc_count)
        else:
            return VectorStoreStatus(
                status="error",
                document_count=0,
                error="Query service not initialized",
                remediation="Restart the API service",
            )

    except Exception as e:
        return VectorStoreStatus(
            status="error",
            document_count=0,
            error=str(e),
            remediation="Check application logs for details",
        )


@router.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute")
async def query_rag(request: Request, query_request: QueryRequest) -> QueryResponse:
    """Execute RAG query with filters.

    Args:
        request: HTTP request for rate limiting
        query_request: Query request with filters

    Returns:
        QueryResponse: Answer with source documents
    """
    try:
        return await query_service.execute_query(
            query=query_request.query,
            region=query_request.region,
            jurisdiction=query_request.jurisdiction,
            topics=query_request.topics,
            max_sources=query_request.max_sources,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    jurisdiction: Optional[str] = QueryParam(
        None, description="Filter by jurisdiction"
    ),
    topic: Optional[str] = QueryParam(None, description="Filter by topic"),
    region: Optional[str] = QueryParam(None, description="Filter by region"),
    status: Optional[str] = QueryParam(None, description="Filter by status"),
    limit: int = QueryParam(50, ge=1, le=500, description="Max results"),
    offset: int = QueryParam(0, ge=0, description="Pagination offset"),
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
    request: Request, query_id: int, feedback_request: FeedbackRequest
) -> FeedbackResponse:
    """Submit feedback for a query.

    Args:
        request: HTTP request for rate limiting
        query_id: Query history ID
        feedback_request: Feedback request with rating and optional text

    Returns:
        FeedbackResponse: Feedback submission confirmation

    Raises:
        HTTPException: If query not found or feedback submission fails
    """
    try:
        success = await query_service.submit_feedback(
            query_id=query_id,
            rating=feedback_request.rating,
            feedback_text=feedback_request.feedback_text,
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


@router.get("/lga-coverage", response_model=CoverageInfo)
async def get_lga_coverage(
    lga_code: Optional[str] = QueryParam(None, description="LGA code (e.g., '40070')"),
    lga_name: Optional[str] = QueryParam(
        None, description="LGA name (e.g., 'City of Adelaide')"
    ),
) -> CoverageInfo:
    """Get document coverage information for a specific LGA.

    Returns coverage metadata including:
    - Number of local documents available
    - Coverage level (high/medium/low/none)
    - Contribution URL for adding new documents

    Args:
        lga_code: Optional LGA code to check coverage for
        lga_name: Optional LGA name to check coverage for

    Returns:
        CoverageInfo: Coverage information and contribution link
    """
    return coverage_service.get_lga_coverage(lga_code=lga_code, lga_name=lga_name)


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
