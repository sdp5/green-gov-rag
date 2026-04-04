"""Document lifecycle state machine service.

Manages transitions between lifecycle states for DocumentFile records and
writes an audit trail to LifecycleEventLog.

Lifecycle states:
    detect               → file URL registered, not yet fetched
    fetch                → ETL downloading the file
    chunk                → text extraction / chunking in progress
    embed                → embedding in progress
    available_for_search → chunks in vector store, searchable
    url_dead             → HTTP 404 detected; no replacement yet; stays in search
    mark_superseded      → admin confirmed replacement URL; to be removed from search
    removed_from_search  → chunks deleted from vector store; terminal state
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from green_gov_rag.models.document import DocumentFile
from green_gov_rag.models.lifecycle import LifecycleEventLog

ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "detect": ["fetch"],
    "fetch": ["chunk", "url_dead"],
    "chunk": ["embed"],
    "embed": ["available_for_search"],
    "available_for_search": ["url_dead"],
    "url_dead": ["available_for_search", "mark_superseded"],
    "mark_superseded": ["removed_from_search"],
    "removed_from_search": [],  # terminal
}


class InvalidLifecycleTransition(Exception):
    """Raised when a requested state transition is not allowed."""


class DocumentLifecycleService:
    """State machine service for DocumentFile lifecycle transitions.

    Usage:
        svc = DocumentLifecycleService(session)
        svc.transition(
            file_id="abc123",
            new_state="url_dead",
            triggered_by="monitor_run",
            http_status=404,
            run_id="uuid-...",
        )
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def transition(
        self,
        file_id: str,
        new_state: str,
        triggered_by: str,
        *,
        reason: Optional[str] = None,
        http_status: Optional[int] = None,
        run_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> DocumentFile:
        """Transition a DocumentFile to a new lifecycle state.

        Args:
            file_id: ID of the DocumentFile to transition.
            new_state: Target lifecycle state.
            triggered_by: What caused the transition ('monitor_run', 'etl_pipeline',
                'api', 'bootstrap').
            reason: Human-readable reason (stored in details).
            http_status: HTTP status code observed (for url_dead transitions).
            run_id: MonitoringLog.run_id if triggered by a monitor run.
            details: Additional context dict merged into the event log.

        Returns:
            The updated DocumentFile.

        Raises:
            ValueError: If file_id not found.
            InvalidLifecycleTransition: If the transition is not allowed.
        """
        file = self._session.get(DocumentFile, file_id)
        if file is None:
            raise ValueError(f"DocumentFile not found: {file_id}")

        current_state = file.lifecycle_state
        allowed = ALLOWED_TRANSITIONS.get(current_state, [])
        if new_state not in allowed:
            raise InvalidLifecycleTransition(
                f"Cannot transition {file_id} from '{current_state}' to '{new_state}'. "
                f"Allowed: {allowed}"
            )

        now = datetime.now(timezone.utc)

        # Update the file
        file.lifecycle_state = new_state
        file.lifecycle_transitioned_at = now
        if http_status is not None:
            file.http_status_code = http_status
            file.http_last_checked_at = now

        # Build event log details
        event_details: dict = {}
        if reason:
            event_details["reason"] = reason
        if details:
            event_details.update(details)

        # Write audit row
        event = LifecycleEventLog(
            file_id=file_id,
            source_id=file.source_id,
            from_state=current_state,
            to_state=new_state,
            triggered_by=triggered_by,
            http_status=http_status,
            run_id=run_id,
            details=event_details or None,
            created_at=now,
        )

        self._session.add(file)
        self._session.add(event)
        self._session.commit()
        self._session.refresh(file)

        return file

    def get_history(self, file_id: str) -> list[LifecycleEventLog]:
        """Return lifecycle event history for a file, newest first."""
        return list(
            self._session.exec(
                select(LifecycleEventLog)
                .where(LifecycleEventLog.file_id == file_id)
                .order_by(LifecycleEventLog.created_at.desc())  # type: ignore[arg-type]
            ).all()
        )

    def get_files_in_state(self, state: str) -> list[DocumentFile]:
        """Return all DocumentFiles currently in the given lifecycle state."""
        return list(
            self._session.exec(
                select(DocumentFile).where(DocumentFile.lifecycle_state == state)
            ).all()
        )
