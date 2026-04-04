"""Monitoring service for automated document update detection.

This service coordinates monitoring of document sources for updates,
using the MonitorableSource interface from the plugin architecture.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc
from sqlmodel import Session, select

from green_gov_rag.api.services.notification import (
    DocumentUpdateNotification,
    NotificationService,
    create_notification_config_from_settings,
)
from green_gov_rag.config import settings
from green_gov_rag.etl.sources.base import (
    ChangeDetectionResult,
    DiscoveredDocument,
    MonitorableSource,
)
from green_gov_rag.etl.sources.registry import DocumentSourceRegistry
from green_gov_rag.models import DocumentFile, DocumentVersion, MonitoringLog
from green_gov_rag.models.base import engine

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring document sources for updates.

    This service:
    - Discovers new documents via web scraping
    - Detects changes to existing documents
    - Tracks version history
    - Logs monitoring runs
    - Triggers ETL pipeline for changed documents
    """

    def __init__(self):
        """Initialize monitoring service."""
        self.registry = DocumentSourceRegistry()

        # Initialize notification service
        self.notification_service = None
        if settings.enable_notifications:
            notification_config = create_notification_config_from_settings(settings)
            self.notification_service = NotificationService(notification_config)
            logger.info("Notifications enabled")

    async def monitor_all_sources(self) -> dict[str, Any]:
        """Monitor all registered sources that support monitoring.

        Returns:
            Summary of monitoring results across all sources
        """
        results: dict[str, Any] = {
            "total_sources": 0,
            "sources_checked": 0,
            "sources_failed": 0,
            "total_discovered": 0,
            "total_updated": 0,
            "total_unchanged": 0,
            "changed_document_ids": [],  # NEW: aggregated changed doc IDs
            "source_results": [],
        }

        # Get all registered sources
        all_sources = self.registry.get_all_sources()
        results["total_sources"] = len(all_sources)

        for source_type, source_class in all_sources.items():
            # Check if source supports monitoring
            if not issubclass(source_class, MonitorableSource):
                logger.info(f"Skipping {source_type}: does not support monitoring")
                continue

            try:
                # Monitor this source
                source_result = await self.monitor_source(source_type)
                results["sources_checked"] += 1
                results["total_discovered"] += source_result["documents_discovered"]
                results["total_updated"] += source_result["documents_updated"]
                results["total_unchanged"] += source_result["documents_unchanged"]
                results["changed_document_ids"].extend(
                    source_result.get("changed_document_ids", [])
                )
                results["source_results"].append(source_result)

            except Exception as e:
                logger.error(
                    f"Failed to monitor source {source_type}: {e}", exc_info=True
                )
                results["sources_failed"] += 1

        return results

    async def monitor_source(self, source_type: str) -> dict[str, Any]:
        """Monitor a specific document source for updates.

        Args:
            source_type: Type identifier for the source (e.g., 'cer_emissions')

        Returns:
            Monitoring results for this source
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        logger.info(f"Starting monitoring run {run_id} for source {source_type}")

        # Create monitoring log
        with Session(engine) as session:
            log = MonitoringLog(
                source_type=source_type,
                run_id=run_id,
                started_at=started_at,
                status="running",
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            log_id = log.id

        try:
            # Get source instance
            source = self.registry.create_source(source_type, config={})

            # Verify it's monitorable
            if not isinstance(source, MonitorableSource):
                raise ValueError(f"Source {source_type} does not support monitoring")

            # Check if monitoring is enabled for this instance
            if not source.is_monitorable():
                logger.info(f"Monitoring disabled for {source_type}")
                return {
                    "source_type": source_type,
                    "status": "skipped",
                    "reason": "monitoring_disabled",
                }

            # Discover documents
            discovered = await source.discover_documents()
            logger.info(f"Discovered {len(discovered)} documents for {source_type}")

            # Track results
            documents_new = 0
            documents_updated = 0
            documents_unchanged = 0
            documents_dead = 0  # URLs returning 404 — no replacement yet
            changed_document_ids = []  # Track changed document IDs

            # Check each discovered document
            for doc in discovered:
                change_result = await self._check_document_change(
                    source, source_type, doc
                )

                # Generate document ID using source plugin (consistent with ingestion)
                doc_id = self._generate_document_id(source, doc.url)

                if change_result.change_type == "new":
                    documents_new += 1
                    changed_document_ids.append(doc_id)
                elif change_result.change_type == "updated":
                    documents_updated += 1
                    changed_document_ids.append(doc_id)
                elif change_result.change_type == "deleted":
                    # URL returned 404 — transition to url_dead, NOT superseded.
                    # Document stays in search until admin provides a replacement URL.
                    documents_dead += 1
                    self._transition_to_url_dead(doc_id, run_id)
                elif change_result.change_type == "unchanged":
                    documents_unchanged += 1

            # Update monitoring log
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            with Session(engine) as session:
                statement = select(MonitoringLog).where(MonitoringLog.id == log_id)
                log_result = session.exec(statement).first()
                if log_result is not None:
                    log_result.completed_at = completed_at
                    log_result.duration_seconds = duration
                    log_result.documents_checked = len(discovered)
                    log_result.documents_discovered = documents_new
                    log_result.documents_updated = documents_updated
                    log_result.documents_unchanged = documents_unchanged
                    log_result.status = "completed"
                    log_result.details = {"documents_dead": documents_dead}
                    session.add(log_result)
                    session.commit()

            result = {
                "source_type": source_type,
                "run_id": run_id,
                "status": "completed",
                "duration_seconds": duration,
                "documents_checked": len(discovered),
                "documents_discovered": documents_new,
                "documents_updated": documents_updated,
                "documents_unchanged": documents_unchanged,
                "documents_dead": documents_dead,
                "changed_document_ids": changed_document_ids,  # for delta indexing
            }

            logger.info(f"Completed monitoring run {run_id}: {result}")
            return result

        except Exception as e:
            # Update monitoring log with error
            with Session(engine) as session:
                statement = select(MonitoringLog).where(MonitoringLog.id == log_id)
                log_result = session.exec(statement).first()
                if log_result is not None:
                    log_result.completed_at = datetime.utcnow()
                    log_result.status = "failed"
                    log_result.error_message = str(e)
                    session.add(log_result)
                    session.commit()

            raise

    async def _check_document_change(
        self,
        source: MonitorableSource,
        source_type: str,
        discovered: DiscoveredDocument,
    ) -> ChangeDetectionResult:
        """Check if a discovered document is new or updated.

        Args:
            source: MonitorableSource instance
            source_type: Source type identifier
            discovered: Discovered document metadata

        Returns:
            ChangeDetectionResult indicating change status
        """
        with Session(engine) as session:
            # Generate document ID using source plugin (consistent with ingestion)
            doc_id = self._generate_document_id(source, discovered.url)

            # Check if we have any versions of this document
            # Use col() to get the SQLAlchemy column for ordering
            from sqlmodel import col

            statement = (
                select(DocumentVersion)
                .where(DocumentVersion.source_id == doc_id)
                .order_by(desc(col(DocumentVersion.version_number)))
            )
            latest_version = session.exec(statement).first()

            if not latest_version:
                # New document - create first version
                logger.info(f"New document discovered: {discovered.title}")
                await self._create_document_version(
                    session, doc_id, discovered, version_number=1, change_type="new"
                )
                return ChangeDetectionResult(
                    has_changed=True, change_type="new", confidence=1.0
                )

            # Check for updates using source's change detection
            known_document = {
                "url": latest_version.source_url,
                "content_hash": latest_version.content_hash,
                "last_checked": latest_version.discovered_at,
                "metadata": latest_version.metadata_,
            }

            change_result = await source.check_for_updates(known_document)

            if change_result.has_changed:
                # Document updated - create new version
                logger.info(
                    f"Document updated: {discovered.title} (confidence: {change_result.confidence})"
                )
                new_version = await self._create_document_version(
                    session,
                    doc_id,
                    discovered,
                    version_number=latest_version.version_number + 1,
                    change_type="updated",
                    change_result=change_result,
                )

                # Mark previous version as superseded
                latest_version.is_current = False
                latest_version.superseded_at = datetime.utcnow()
                session.add(latest_version)
                session.commit()

                # Send notification if enabled
                if self.notification_service:
                    try:
                        notification = DocumentUpdateNotification(
                            document_id=doc_id,
                            document_title=discovered.title,
                            source_url=discovered.url,
                            old_version=latest_version.version_number,
                            new_version=new_version.version_number,
                            change_summary=change_result.details,
                            confidence_score=change_result.confidence,
                            discovered_at=datetime.utcnow(),
                        )
                        await (
                            self.notification_service.send_document_update_notification(
                                notification
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to send notification: {e}", exc_info=True)

            return change_result

    async def _create_document_version(
        self,
        session: Session,
        doc_id: str,
        discovered: DiscoveredDocument,
        version_number: int,
        change_type: str,
        change_result: ChangeDetectionResult | None = None,
    ) -> DocumentVersion:
        """Create a new document version record.

        Args:
            session: Database session
            doc_id: Document identifier
            discovered: Discovered document metadata
            version_number: Version number (1, 2, 3...)
            change_type: 'new' or 'updated'
            change_result: Optional change detection result

        Returns:
            Created DocumentVersion instance
        """
        # Calculate content hash if not provided
        content_hash = discovered.content_hash or self._hash_url(discovered.url)

        version = DocumentVersion(
            source_id=doc_id,
            version_number=version_number,
            content_hash=content_hash,
            source_url=discovered.url,
            file_size_bytes=discovered.file_size_bytes,
            change_type=change_type,
            change_summary=change_result.details if change_result else None,
            confidence_score=change_result.confidence if change_result else 1.0,
            discovered_at=datetime.utcnow(),
            remote_last_modified=discovered.last_modified,
            metadata_=discovered.metadata,
            status="discovered",
            is_current=True,
        )

        session.add(version)
        session.commit()
        session.refresh(version)

        return version

    def _transition_to_url_dead(self, doc_id: str, run_id: str) -> None:
        """Transition a DocumentFile to url_dead when its URL returns 404.

        The document stays in search until an admin provides a replacement URL.
        Uses DocumentLifecycleService to enforce valid transitions only.
        """
        from green_gov_rag.api.services.lifecycle_service import (
            DocumentLifecycleService,
            InvalidLifecycleTransition,
        )
        from green_gov_rag.models.base import engine

        with Session(engine) as session:
            # Find the DocumentFile whose id matches doc_id
            file_row = session.exec(
                select(DocumentFile).where(DocumentFile.id == doc_id)
            ).first()
            if file_row is None:
                logger.debug("_transition_to_url_dead: no DocumentFile for %s", doc_id)
                return

            svc = DocumentLifecycleService(session)
            try:
                svc.transition(
                    file_id=file_row.id,
                    new_state="url_dead",
                    triggered_by="monitor_run",
                    http_status=404,
                    run_id=run_id,
                    reason="URL returned HTTP 404 — document may be superseded",
                )
                logger.info("Transitioned %s to url_dead", doc_id)
            except InvalidLifecycleTransition as exc:
                # Already in url_dead or a terminal state — that's fine
                logger.debug("Skipping lifecycle transition for %s: %s", doc_id, exc)

    def _generate_document_id(self, source: Any, url: str) -> str:
        """Generate unique document ID using source plugin (single source of truth).

        Uses the source plugin's get_document_id() method to ensure consistency
        between monitoring and ingestion. This is critical for delta indexing.

        Args:
            source: DocumentSource instance (with get_document_id method)
            url: Document URL

        Returns:
            Unique document identifier
        """
        # Use plugin's document ID generation (same as ingestion)
        if hasattr(source, "get_document_id"):
            return source.get_document_id(url)

        # Fallback for non-plugin sources (shouldn't happen in production)
        logger.warning(f"Source {source} doesn't have get_document_id, using fallback")
        content = f"{source.get_source_type()}:{url}".encode("utf-8")
        hash_hex = hashlib.sha256(content).hexdigest()[:16]
        return f"{source.get_source_type()}_{hash_hex}"

    def _hash_url(self, url: str) -> str:
        """Generate SHA256 hash of URL as fallback content hash.

        Args:
            url: Document URL

        Returns:
            SHA256 hash hex string
        """
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    async def get_monitoring_history(
        self,
        source_type: str | None = None,
        limit: int = 10,
    ) -> list[MonitoringLog]:
        """Get recent monitoring logs.

        Args:
            source_type: Optional filter by source type
            limit: Maximum number of logs to return

        Returns:
            List of recent monitoring logs
        """
        from sqlmodel import col

        with Session(engine) as session:
            statement = select(MonitoringLog).order_by(
                desc(col(MonitoringLog.started_at))
            )

            if source_type:
                statement = statement.where(MonitoringLog.source_type == source_type)

            statement = statement.limit(limit)

            logs = session.exec(statement).all()
            return list(logs)

    async def get_document_versions(
        self,
        document_id: str,
    ) -> list[DocumentVersion]:
        """Get version history for a document.

        Args:
            document_id: Document identifier

        Returns:
            List of versions, newest first
        """
        from sqlmodel import col

        with Session(engine) as session:
            statement = (
                select(DocumentVersion)
                .where(DocumentVersion.source_id == document_id)
                .order_by(desc(col(DocumentVersion.version_number)))
            )

            versions = session.exec(statement).all()
            return list(versions)
