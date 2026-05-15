"""Admin API endpoints."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Request
from sqlmodel import Session, func, select

from green_gov_rag.api.routes import limiter
from green_gov_rag.api.schemas import (
    AdminActionResponse,
    AdminDocumentDetailResponse,
    AdminDocumentListResponse,
    DashboardStats,
    DownloadFailureGroup,
    DownloadFailureItem,
    DownloadFailureListResponse,
    DownloadFailureSummaryResponse,
    QueryAnalyticsResponse,
    SystemHealthResponse,
)
from green_gov_rag.models import DocumentFile, DocumentSource, QueryHistory
from green_gov_rag.models.base import engine

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardStats)
@limiter.limit("10/minute")
async def get_dashboard_stats(request: Request) -> DashboardStats:
    """Get dashboard statistics.

    Returns overview metrics for admin dashboard.
    Rate limited to 10 requests per minute.
    """
    with Session(engine) as session:
        # Document stats
        total_docs = session.exec(
            select(func.count()).select_from(DocumentSource)
        ).one()
        processing = session.exec(
            select(func.count())
            .select_from(DocumentSource)
            .where(DocumentSource.status == "processing")
        ).one()
        failed = session.exec(
            select(func.count())
            .select_from(DocumentSource)
            .where(DocumentSource.status == "failed")
        ).one()
        completed = session.exec(
            select(func.count())
            .select_from(DocumentSource)
            .where(DocumentSource.status == "completed")
        ).one()
        download_failed = session.exec(
            select(func.count())
            .select_from(DocumentFile)
            .where(DocumentFile.status == "download_failed")
        ).one()
        # needs_attention requires Python-side filtering (JSON parsing)
        failed_files = session.exec(
            select(DocumentFile).where(DocumentFile.status == "download_failed")
        ).all()
        needs_attention = sum(1 for f in failed_files if f.needs_attention)

        # Query stats
        total_queries = session.exec(
            select(func.count()).select_from(QueryHistory)
        ).one()

        # Recent queries
        recent_queries = session.exec(
            select(QueryHistory)
            .order_by(QueryHistory.created_at.desc())  # type: ignore[attr-defined]
            .limit(10)
        ).all()

        return DashboardStats(
            documents={
                "total": total_docs,
                "processing": processing,
                "failed": failed,
                "completed": completed,
                "download_failed": download_failed,
                "needs_attention": needs_attention,
            },
            queries={
                "total": total_queries,
                "recent": [
                    {
                        "id": q.id,
                        "query_text": q.query_text,
                        "created_at": q.created_at.isoformat()
                        if q.created_at
                        else None,
                        "response_time_ms": q.response_time_ms,
                    }
                    for q in recent_queries
                ],
            },
        )


@router.get("/documents", response_model=AdminDocumentListResponse)
@limiter.limit("10/minute")
async def list_documents(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    jurisdiction: str | None = None,
) -> AdminDocumentListResponse:
    """List documents with filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum records to return
        status: Filter by status
        jurisdiction: Filter by jurisdiction
    """
    with Session(engine) as session:
        query = select(DocumentSource)

        if status:
            query = query.where(DocumentSource.status == status)
        if jurisdiction:
            query = query.where(DocumentSource.jurisdiction == jurisdiction)

        query = query.offset(skip).limit(limit)
        documents = session.exec(query).all()

        from green_gov_rag.api.schemas import AdminDocumentItem

        return AdminDocumentListResponse(
            documents=[
                AdminDocumentItem(
                    id=doc.id,
                    title=doc.title,
                    jurisdiction=doc.jurisdiction,
                    status=doc.status,
                    created_at=doc.created_at.isoformat() if doc.created_at else None,
                    error_message=doc.error_message,
                )
                for doc in documents
            ]
        )


@router.get("/documents/{document_id}", response_model=AdminDocumentDetailResponse)
@limiter.limit("10/minute")
async def get_document(
    request: Request, document_id: str
) -> AdminDocumentDetailResponse:
    """Get document details."""
    from fastapi import HTTPException

    with Session(engine) as session:
        doc = session.get(DocumentSource, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        return AdminDocumentDetailResponse(
            id=doc.id,
            title=doc.title,
            source_url=doc.source_url,
            jurisdiction=doc.jurisdiction,
            topic=doc.topic,
            region=doc.region,
            status=doc.status,
            error_message=doc.error_message,
            created_at=doc.created_at.isoformat() if doc.created_at else None,
            updated_at=doc.updated_at.isoformat() if doc.updated_at else None,
        )


@router.post("/documents/{document_id}/reprocess", response_model=AdminActionResponse)
@limiter.limit("10/minute")
async def reprocess_document(request: Request, document_id: str) -> AdminActionResponse:
    """Trigger document reprocessing.

    Updates document status to 'pending' to trigger reprocessing.
    Also invalidates cache entries that use this document.
    """
    from fastapi import HTTPException

    from green_gov_rag.api.routes import query_service

    with Session(engine) as session:
        doc = session.get(DocumentSource, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        doc.status = "pending"
        doc.error_message = None
        session.add(doc)
        session.commit()

        # Invalidate cache entries for this document
        if query_service.cache_service:
            invalidated = query_service.cache_service.invalidate_by_document(
                document_id
            )
            message = f"Document reprocessing triggered. Invalidated {invalidated} cache entries."
        else:
            message = "Document reprocessing triggered"

        return AdminActionResponse(
            status="triggered",
            document_id=document_id,
            message=message,
        )


@router.delete("/documents/{document_id}", response_model=AdminActionResponse)
@limiter.limit("10/minute")
async def delete_document(request: Request, document_id: str) -> AdminActionResponse:
    """Delete a document.

    Also invalidates cache entries that use this document.
    """
    from fastapi import HTTPException

    from green_gov_rag.api.routes import query_service

    with Session(engine) as session:
        doc = session.get(DocumentSource, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        session.delete(doc)
        session.commit()

        # Invalidate cache entries for this document
        if query_service.cache_service:
            invalidated = query_service.cache_service.invalidate_by_document(
                document_id
            )
            message = f"Document deleted successfully. Invalidated {invalidated} cache entries."
        else:
            message = "Document deleted successfully"

        return AdminActionResponse(
            status="deleted",
            document_id=document_id,
            message=message,
        )


@router.get("/analytics/queries", response_model=QueryAnalyticsResponse)
@limiter.limit("10/minute")
async def get_query_analytics(
    request: Request,
    days: int = 7,
    session_id: Optional[str] = None,
) -> QueryAnalyticsResponse:
    """Get query analytics for last N days.

    Args:
        days: Number of days to analyze (default: 7)
        session_id: Optional session ID to filter by user (for user-specific analytics)
    """
    from datetime import datetime, timedelta

    with Session(engine) as session:
        cutoff_date = datetime.now() - timedelta(days=days)

        # Build base query filter
        base_filter = QueryHistory.created_at >= cutoff_date
        if session_id:
            base_filter = (QueryHistory.created_at >= cutoff_date) & (
                QueryHistory.session_id == session_id
            )

        # Total queries in period
        total = session.exec(
            select(func.count()).select_from(QueryHistory).where(base_filter)
        ).one()

        # Average response time
        avg_response = session.exec(
            select(func.avg(QueryHistory.response_time_ms))
            .select_from(QueryHistory)
            .where(base_filter)
        ).one()

        # Top topics
        top_topics = session.exec(
            select(QueryHistory.topic_filter, func.count())
            .where(base_filter)
            .where(QueryHistory.topic_filter.is_not(None))  # type: ignore[union-attr]
            .group_by(QueryHistory.topic_filter)
            .order_by(func.count().desc())
            .limit(5)
        ).all()

        return QueryAnalyticsResponse(
            period_days=days,
            total_queries=total,
            avg_response_time_ms=round(avg_response, 2) if avg_response else 0,
            top_topics=[
                {"topic": topic, "count": count} for topic, count in top_topics
            ],
        )


@router.get("/system/health", response_model=SystemHealthResponse)
@limiter.limit("10/minute")
async def get_system_health(request: Request) -> SystemHealthResponse:
    """Get system health status.

    Checks database connectivity and basic system status.
    """
    from green_gov_rag.config import settings

    database_status = "unknown"

    # Check database
    try:
        with Session(engine) as session:
            session.exec(select(func.count()).select_from(DocumentSource)).one()
            database_status = "connected"
    except Exception as e:
        database_status = f"error: {str(e)}"

    return SystemHealthResponse(
        database=database_status,
        vector_store=settings.vector_store_type,
        llm_provider=settings.llm_provider,
    )


def _get_failed_download_pairs() -> list[tuple[DocumentFile, DocumentSource]]:
    """Fetch all download_failed files joined with their source."""
    with Session(engine) as session:
        results = session.exec(
            select(DocumentFile, DocumentSource)
            .where(DocumentFile.status == "download_failed")
            .where(DocumentFile.source_id == DocumentSource.id)
        ).all()
        # Expunge so objects are usable outside session
        pairs = []
        for doc_file, doc_source in results:
            session.expunge(doc_file)
            session.expunge(doc_source)
            pairs.append((doc_file, doc_source))
        return pairs


def _to_failure_item(
    doc_file: DocumentFile, doc_source: DocumentSource
) -> DownloadFailureItem:
    """Convert a file+source pair to a DownloadFailureItem schema."""
    return DownloadFailureItem(
        file_id=doc_file.id,
        source_id=doc_source.id,
        source_title=doc_source.title,
        file_url=doc_file.file_url,
        failure_reason=doc_file.failure_reason,
        attempt_count=doc_file.attempt_count,
        needs_attention=doc_file.needs_attention,
        last_attempt_at=doc_file.last_attempt_at,
        status_code=(doc_file._parse_error_data() or {}).get("status_code"),
        jurisdiction=doc_source.jurisdiction,
        state=doc_source.state_code,
        lga_names=doc_source.source_lga_names,
    )


@router.get(
    "/download-failures",
    response_model=DownloadFailureSummaryResponse,
)
@limiter.limit("10/minute")
async def get_download_failures(
    request: Request,
    group_by: str = "reason",
) -> DownloadFailureSummaryResponse:
    """Get download failures grouped by a dimension.

    Args:
        group_by: Grouping dimension — reason, state, lga, or jurisdiction.
    """
    pairs = _get_failed_download_pairs()

    # Build grouping key function
    def _get_group_keys(
        doc_file: DocumentFile, doc_source: DocumentSource
    ) -> list[str]:
        if group_by == "reason":
            return [doc_file.failure_reason or "unknown"]
        if group_by == "state":
            return [doc_source.state_code or "unknown"]
        if group_by == "lga":
            names = doc_source.source_lga_names
            return names if names else [doc_source.region or "unknown"]
        if group_by == "jurisdiction":
            return [doc_source.jurisdiction]
        return ["unknown"]

    # Group
    grouped: dict[str, list[tuple[DocumentFile, DocumentSource]]] = defaultdict(list)
    for doc_file, doc_source in pairs:
        for key in _get_group_keys(doc_file, doc_source):
            grouped[key].append((doc_file, doc_source))

    total_needs_attention = sum(1 for f, _ in pairs if f.needs_attention)

    groups = []
    for key, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        na_count = sum(1 for f, _ in items if f.needs_attention)
        sample = [f.file_url for f, _ in items[:3]]
        groups.append(
            DownloadFailureGroup(
                group_key=key,
                group_label=key,
                count=len(items),
                needs_attention_count=na_count,
                sample_urls=sample,
            )
        )

    return DownloadFailureSummaryResponse(
        group_by=group_by,
        total_failures=len(pairs),
        total_needs_attention=total_needs_attention,
        groups=groups,
    )


@router.get(
    "/download-failures/detail",
    response_model=DownloadFailureListResponse,
)
@limiter.limit("10/minute")
async def list_download_failures(
    request: Request,
    state: str | None = None,
    lga_name: str | None = None,
    failure_reason: str | None = None,
    jurisdiction: str | None = None,
    needs_attention_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> DownloadFailureListResponse:
    """List download failures with filters.

    Filters by state, LGA name, failure reason, jurisdiction, and
    needs_attention status. Filtering on JSON fields (state, lga, reason)
    is done in Python after the SQL query.
    """
    pairs = _get_failed_download_pairs()

    # Apply filters
    filtered = []
    for doc_file, doc_source in pairs:
        if jurisdiction and doc_source.jurisdiction != jurisdiction:
            continue
        if state and doc_source.state_code != state:
            continue
        if lga_name and lga_name not in doc_source.source_lga_names:
            continue
        if failure_reason and doc_file.failure_reason != failure_reason:
            continue
        if needs_attention_only and not doc_file.needs_attention:
            continue
        filtered.append((doc_file, doc_source))

    total = len(filtered)
    page = filtered[skip : skip + limit]

    return DownloadFailureListResponse(
        total=total,
        failures=[_to_failure_item(f, s) for f, s in page],
    )


@router.post(
    "/download-failures/{file_id}/retry",
    response_model=AdminActionResponse,
)
@limiter.limit("10/minute")
async def retry_download(request: Request, file_id: str) -> AdminActionResponse:
    """Reset a failed download for retry on next ingest run.

    Preserves attempt history but resets status to 'pending' so the
    next ingest run will re-attempt the download.
    """
    import json

    from fastapi import HTTPException

    with Session(engine) as session:
        doc_file = session.get(DocumentFile, file_id)
        if not doc_file:
            raise HTTPException(status_code=404, detail="File not found")
        if doc_file.status != "download_failed":
            raise HTTPException(
                status_code=400,
                detail=f"File status is '{doc_file.status}', not 'download_failed'",
            )

        # Preserve history but append admin_reset marker
        error_data = {}
        if doc_file.error_message:
            try:
                error_data = json.loads(doc_file.error_message)
            except (json.JSONDecodeError, TypeError):
                error_data = {}

        history = error_data.get("attempt_history", [])
        from datetime import datetime, timezone

        history.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "reason": "admin_reset",
                "status_code": None,
            }
        )
        error_data["attempt_history"] = history
        doc_file.error_message = json.dumps(error_data)
        doc_file.status = "pending"

        session.add(doc_file)
        session.commit()

    return AdminActionResponse(
        status="reset",
        document_id=file_id,
        message="Download reset to pending. Will retry on next ingest run.",
    )


@router.get("/cache/metrics")
@limiter.limit("10/minute")
async def get_cache_metrics(request: Request) -> dict:
    """Get cache performance metrics.

    Returns cache hit rate, cost savings, and other statistics.
    """
    from green_gov_rag.api.routes import query_service

    if not query_service.cache_service:
        return {"error": "Cache is not enabled"}

    return query_service.cache_service.get_metrics()


@router.post("/cache/clear")
@limiter.limit("10/minute")
async def clear_cache(request: Request) -> dict:
    """Clear all cache entries.

    Use with caution - this will remove all cached responses.
    """
    from green_gov_rag.api.routes import query_service

    if not query_service.cache_service:
        return {"error": "Cache is not enabled"}

    query_service.cache_service.clear()
    return {"status": "success", "message": "Cache cleared"}
