"""API routes for GreenGovRAG."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi import Query as QueryParam
from fastapi.responses import FileResponse, RedirectResponse, Response
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
        # Extract traffic analytics from request headers
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        referer = request.headers.get("referer")

        return await query_service.execute_query(
            query=query_request.query,
            region=query_request.region,
            jurisdiction=query_request.jurisdiction,
            topics=query_request.topics,
            max_sources=query_request.max_sources,
            session_id=query_request.session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
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

    Raises:
        HTTPException: If database error occurs
    """
    try:
        return document_service.get_documents(
            jurisdiction=jurisdiction,
            topic=topic,
            region=region,
            status=status,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Database error listing documents: {e}")
        raise HTTPException(status_code=503, detail="Database temporarily unavailable")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str) -> DocumentResponse:
    """Get document by ID.

    Args:
        document_id: Document ID

    Returns:
        DocumentResponse: Document details

    Raises:
        HTTPException: If document not found or database error
    """
    try:
        doc = document_service.get_document_by_id(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Database error fetching document {document_id}: {e}")
        raise HTTPException(status_code=503, detail="Database temporarily unavailable")


@router.get("/documents/files/{filename}")
async def serve_pdf(filename: str) -> Response:
    """Serve PDF files for deep linking and viewing.

    This endpoint serves source PDF documents with cloud-aware implementation:
    - AWS: Generates presigned S3 URLs (5 min TTL)
    - Azure: Generates SAS token URLs (5 min TTL)
    - Local: Serves from data/raw directory

    Args:
        filename: PDF filename to serve

    Returns:
        FileResponse or RedirectResponse: PDF file or redirect to cloud URL

    Raises:
        HTTPException: If file not found or not a PDF

    Example:
        GET /api/documents/files/ncc2022-volume-one.pdf
        Returns PDF file that can be viewed with #page=48 anchor
    """
    from green_gov_rag.config import settings

    # Security: Only allow PDF files
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files can be served via this endpoint"
        )

    # Security: Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Cloud-aware implementation
    from green_gov_rag.types import CloudProvider

    if settings.cloud_provider == CloudProvider.AWS:
        # Generate presigned S3 URL (5 minute expiry)
        try:
            import boto3
            from botocore.config import Config

            config = Config(signature_version="s3v4")
            s3_client = boto3.client(
                "s3",
                region_name=settings.aws_region or settings.cloud_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                config=config,
            )

            # Generate presigned URL
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.storage_container,
                    "Key": f"raw/{filename}",
                },
                ExpiresIn=300,  # 5 minutes
            )

            return RedirectResponse(url=url)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to generate S3 presigned URL: {str(e)}"
            )

    elif settings.cloud_provider == CloudProvider.AZURE:
        # Generate Azure Blob SAS token URL (5 minute expiry)
        try:
            from datetime import datetime, timedelta, timezone

            from azure.storage.blob import BlobServiceClient, generate_blob_sas

            blob_service_client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
            blob_client = blob_service_client.get_blob_client(
                container=settings.storage_container, blob=f"raw/{filename}"
            )

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=settings.storage_container,
                blob_name=f"raw/{filename}",
                account_key=blob_service_client.credential.account_key,
                permission="r",  # Read-only
                expiry=datetime.now(timezone.utc) + timedelta(minutes=5),
            )

            url = f"{blob_client.url}?{sas_token}"

            return RedirectResponse(url=url)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate Azure SAS token: {str(e)}",
            )

    else:
        # Local development: serve from filesystem
        raw_dir = Path(settings.raw_data_dir)
        pdf_path = None

        # Search recursively for the file
        for pdf_file in raw_dir.rglob(filename):
            if pdf_file.is_file():
                pdf_path = pdf_file
                break

        if not pdf_path or not pdf_path.exists():
            raise HTTPException(
                status_code=404, detail=f"PDF file '{filename}' not found"
            )

        # Return file with appropriate headers for PDF viewing
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=filename,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            },
        )


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

    Raises:
        HTTPException: If database error occurs
    """
    try:
        return analytics_service.get_stats()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Database error fetching analytics: {e}")
        raise HTTPException(status_code=503, detail="Analytics temporarily unavailable")


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

    Raises:
        HTTPException: If database error occurs
    """
    try:
        return coverage_service.get_lga_coverage(lga_code=lga_code, lga_name=lga_name)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Database error fetching LGA coverage: {e}")
        raise HTTPException(
            status_code=503, detail="Coverage data temporarily unavailable"
        )


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
