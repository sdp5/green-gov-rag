"""Admin API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from sqlmodel import Session, func, select

from green_gov_rag.api.schemas import (
    AdminActionResponse,
    AdminDocumentDetailResponse,
    AdminDocumentListResponse,
    DashboardStats,
    QueryAnalyticsResponse,
    SystemHealthResponse,
)
from green_gov_rag.models import DocumentSource, QueryHistory
from green_gov_rag.models.base import engine

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats() -> DashboardStats:
    """Get dashboard statistics.

    Returns overview metrics for admin dashboard.
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
async def list_documents(
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
async def get_document(document_id: str) -> AdminDocumentDetailResponse:
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
async def reprocess_document(document_id: str) -> AdminActionResponse:
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
async def delete_document(document_id: str) -> AdminActionResponse:
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
async def get_query_analytics(
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
async def get_system_health() -> SystemHealthResponse:
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


@router.get("/cache/metrics")
async def get_cache_metrics() -> dict:
    """Get cache performance metrics.

    Returns cache hit rate, cost savings, and other statistics.
    """
    from green_gov_rag.api.routes import query_service

    if not query_service.cache_service:
        return {"error": "Cache is not enabled"}

    return query_service.cache_service.get_metrics()


@router.post("/cache/clear")
async def clear_cache() -> dict:
    """Clear all cache entries.

    Use with caution - this will remove all cached responses.
    """
    from green_gov_rag.api.routes import query_service

    if not query_service.cache_service:
        return {"error": "Cache is not enabled"}

    query_service.cache_service.clear()
    return {"status": "success", "message": "Cache cleared"}
