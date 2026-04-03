"""Admin API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from sqlmodel import Session, func, select

from green_gov_rag.api.routes import limiter
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


# =============================================================================
# Lifecycle Dashboard Endpoints
# =============================================================================


@router.get("/lifecycle/summary", response_model=None)
@limiter.limit("30/minute")
async def get_lifecycle_summary(request: Request) -> dict:
    """Count of DocumentFiles in each lifecycle state."""
    from green_gov_rag.api.schemas.lifecycle import LifecycleSummary
    from green_gov_rag.models.document import DocumentFile, DocumentSource
    from green_gov_rag.models.document_version import MonitoringLog

    with Session(engine) as session:
        states = [
            "detect",
            "fetch",
            "chunk",
            "embed",
            "available_for_search",
            "url_dead",
            "mark_superseded",
            "removed_from_search",
        ]
        counts: dict[str, int] = {}
        for state in states:
            counts[state] = session.exec(
                select(func.count())
                .select_from(DocumentFile)
                .where(DocumentFile.lifecycle_state == state)
            ).one()

        total_files = session.exec(select(func.count()).select_from(DocumentFile)).one()
        total_sources = session.exec(
            select(func.count()).select_from(DocumentSource)
        ).one()

        last_run = session.exec(
            select(MonitoringLog)
            .where(MonitoringLog.status == "completed")
            .order_by(MonitoringLog.completed_at.desc())  # type: ignore[arg-type]
        ).first()

        return LifecycleSummary(
            **counts,
            total_files=total_files,
            total_sources=total_sources,
            last_monitoring_run=last_run.completed_at if last_run else None,
        ).model_dump()


@router.get("/lifecycle/documents/by-lga", response_model=None)
@limiter.limit("20/minute")
async def get_documents_by_lga(
    request: Request,
    lifecycle_state: Optional[str] = None,
) -> dict:
    """Document registry grouped by LGA.

    Federal/state documents (applies_to_all_lgas=true) appear under 'All LGAs'.
    Each group lists documents with their lifecycle state.
    Superseded documents show a prompt for the admin to provide a replacement URL.

    Filter by lifecycle_state (e.g. 'url_dead') to see only documents needing attention.
    """
    from collections import defaultdict

    from green_gov_rag.api.schemas.lifecycle import (
        LGADocumentGroup,
        LGALifecycleResponse,
        LifecycleDocumentEntry,
    )
    from green_gov_rag.models.document import DocumentFile, DocumentSource

    with Session(engine) as session:
        query = select(DocumentFile, DocumentSource).join(
            DocumentSource, DocumentFile.source_id == DocumentSource.id
        )
        if lifecycle_state:
            query = query.where(DocumentFile.lifecycle_state == lifecycle_state)

        rows = session.exec(query).all()

        # Group by LGA
        groups: dict[str, list[LifecycleDocumentEntry]] = defaultdict(list)

        for file_row, source_row in rows:
            spatial = source_row.spatial_metadata or {}
            applies_to_all = spatial.get("applies_to_all_lgas", False)
            lga_names: list[str] = spatial.get("lga_names") or []

            entry = LifecycleDocumentEntry(
                file_id=file_row.id,
                source_id=source_row.id,
                title=source_row.title,
                jurisdiction=source_row.jurisdiction,
                topic=source_row.topic,
                lga_names=lga_names,
                applies_to_all_lgas=applies_to_all,
                file_url=file_row.file_url,
                lifecycle_state=file_row.lifecycle_state,
                lifecycle_transitioned_at=file_row.lifecycle_transitioned_at,
                http_status_code=file_row.http_status_code,
                http_last_checked_at=file_row.http_last_checked_at,
                superseded_by_url=file_row.superseded_by_url,
            )

            if applies_to_all or not lga_names:
                groups["All LGAs"].append(entry)
            else:
                for lga in lga_names:
                    groups[lga].append(entry)

        group_list = [
            LGADocumentGroup(lga_name=lga, documents=docs)
            for lga, docs in sorted(groups.items())
        ]
        # Put "All LGAs" first
        group_list.sort(key=lambda g: (g.lga_name != "All LGAs", g.lga_name))

        total_files = sum(len(g.documents) for g in group_list)
        return LGALifecycleResponse(
            groups=group_list,
            total_lgas=len(group_list),
            total_files=total_files,
        ).model_dump()


@router.get("/lifecycle/documents/{file_id}/history", response_model=None)
@limiter.limit("30/minute")
async def get_document_lifecycle_history(request: Request, file_id: str) -> dict:
    """Lifecycle event history for a specific document file (for timeline view)."""
    from green_gov_rag.api.schemas.lifecycle import LifecycleEventEntry
    from green_gov_rag.api.services.lifecycle_service import DocumentLifecycleService

    with Session(engine) as session:
        svc = DocumentLifecycleService(session)
        events = svc.get_history(file_id)
        return {
            "file_id": file_id,
            "events": [
                LifecycleEventEntry(
                    id=e.id,
                    from_state=e.from_state,
                    to_state=e.to_state,
                    triggered_by=e.triggered_by,
                    http_status=e.http_status,
                    run_id=e.run_id,
                    details=e.details,
                    created_at=e.created_at,
                ).model_dump()
                for e in events
            ],
        }


@router.post("/lifecycle/documents/{file_id}/replace", response_model=None)
@limiter.limit("20/minute")
async def replace_superseded_document(
    request: Request, file_id: str, body: dict
) -> dict:
    """Admin provides a replacement URL for a url_dead document.

    This marks the old file as superseded and registers the new URL
    for ingestion on the next monitoring run.

    Body: {"new_url": "https://..."}
    """
    from datetime import timezone

    from green_gov_rag.api.services.lifecycle_service import (
        DocumentLifecycleService,
        InvalidLifecycleTransition,
    )
    from green_gov_rag.models.document import DocumentFile

    new_url: str = body.get("new_url", "").strip()
    if not new_url.startswith("http"):
        return {"error": "new_url must be a valid http/https URL"}

    with Session(engine) as session:
        old_file = session.get(DocumentFile, file_id)
        if old_file is None:
            return {"error": f"DocumentFile {file_id} not found"}

        svc = DocumentLifecycleService(session)

        # Transition old file: url_dead → mark_superseded
        try:
            svc.transition(
                file_id=file_id,
                new_state="mark_superseded",
                triggered_by="api",
                reason=f"Admin provided replacement URL: {new_url}",
                details={"replacement_url": new_url},
            )
        except InvalidLifecycleTransition as exc:
            return {"error": str(exc)}

        # Record the replacement URL on the old file
        old_file.superseded_by_url = new_url
        session.add(old_file)

        # Register new DocumentFile with lifecycle_state='detect'
        now = datetime.now(timezone.utc)
        filename = new_url.rsplit("/", 1)[-1] or new_url
        # Reuse same source_id as the superseded file
        new_file_id = f"{old_file.source_id}_{filename}"
        existing = session.get(DocumentFile, new_file_id)
        if existing is None:
            new_file = DocumentFile(
                id=new_file_id,
                source_id=old_file.source_id,
                filename=filename,
                file_url=new_url,
                content_hash="",
                lifecycle_state="detect",
                discovered_at=now,
            )
            session.add(new_file)

        session.commit()

        return {
            "status": "success",
            "superseded_file_id": file_id,
            "new_file_id": new_file_id,
            "new_url": new_url,
            "message": (
                "Old document marked as superseded. "
                "New URL registered for ingestion on next monitoring run."
            ),
        }


@router.post("/lifecycle/documents/{file_id}/mark-superseded", response_model=None)
@limiter.limit("10/minute")
async def manual_mark_superseded(request: Request, file_id: str) -> dict:
    """Manually force a document to mark_superseded (admin override).

    Use when a document is known to be outdated even if its URL is still live.
    The document must already be in url_dead state.
    """
    from green_gov_rag.api.services.lifecycle_service import (
        DocumentLifecycleService,
        InvalidLifecycleTransition,
    )

    with Session(engine) as session:
        svc = DocumentLifecycleService(session)
        try:
            svc.transition(
                file_id=file_id,
                new_state="mark_superseded",
                triggered_by="api",
                reason="Manual admin override",
            )
        except InvalidLifecycleTransition as exc:
            return {"error": str(exc)}
        return {"status": "success", "file_id": file_id, "new_state": "mark_superseded"}


@router.post("/documents", response_model=None)
@limiter.limit("10/minute")
async def register_document(request: Request, body: dict) -> dict:
    """Register a new document source directly via API (no YAML PR needed).

    The new document enters lifecycle_state='detect' and will be picked up
    for ingestion on the next monitoring run.

    Body fields: title, source_url, download_urls, jurisdiction, category,
                 topic, region (optional), esg_metadata (optional),
                 spatial_metadata (optional)
    """
    from datetime import timezone

    from green_gov_rag.etl.sources.factory import DocumentSourceFactory
    from green_gov_rag.models.document import DocumentFile, DocumentSource

    required = [
        "title",
        "source_url",
        "download_urls",
        "jurisdiction",
        "category",
        "topic",
    ]
    for field_name in required:
        if not body.get(field_name):
            return {"error": f"Missing required field: {field_name}"}

    download_urls: list[str] = body["download_urls"]
    if not download_urls:
        return {"error": "download_urls must not be empty"}

    factory = DocumentSourceFactory()
    try:
        source_plugin = factory.create_source(body)
    except Exception as exc:
        return {"error": f"Failed to create source plugin: {exc}"}

    source_id = source_plugin.get_document_id(download_urls[0])
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        existing = session.get(DocumentSource, source_id)
        if existing is not None:
            return {"error": f"Source {source_id} already registered"}

        new_source = DocumentSource(
            id=source_id,
            title=body["title"],
            source_url=body["source_url"],
            jurisdiction=body["jurisdiction"],
            topic=body["topic"],
            region=body.get("region"),
            category=body.get("category"),
            esg_metadata=body.get("esg_metadata"),
            spatial_metadata=body.get("spatial_metadata"),
            status="pending",
            db_bootstrapped_at=None,  # Not from YAML
        )
        session.add(new_source)

        file_ids = []
        for url in download_urls:
            file_id = source_plugin.get_document_id(url)
            filename = url.rsplit("/", 1)[-1] or url
            new_file = DocumentFile(
                id=file_id,
                source_id=source_id,
                filename=filename,
                file_url=url,
                content_hash="",
                lifecycle_state="detect",
                discovered_at=now,
            )
            session.add(new_file)
            file_ids.append(file_id)

        session.commit()

    return {
        "source_id": source_id,
        "file_ids": file_ids,
        "lifecycle_state": "detect",
        "message": "Document registered. Will be ingested on next monitoring run.",
    }
