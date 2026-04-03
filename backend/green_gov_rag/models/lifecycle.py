"""Lifecycle event log model for document state machine audit trail."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class LifecycleEventLog(SQLModel, table=True):
    """Audit trail for document lifecycle state transitions.

    Every time a DocumentFile moves from one lifecycle state to another,
    a row is written here. This enables the per-document timeline view
    in the admin dashboard.

    States:
        detect → fetch → chunk → embed → available_for_search
        available_for_search → url_dead  (404 detected, no replacement yet)
        url_dead → mark_superseded       (admin provides replacement URL)
        url_dead → available_for_search  (URL recovered / was transient)
        mark_superseded → removed_from_search
    """

    __tablename__ = "lifecycle_event_log"

    id: Optional[int] = Field(default=None, primary_key=True)

    file_id: str = Field(
        index=True,
        foreign_key="document_files.id",
        description="The DocumentFile that transitioned",
    )
    source_id: str = Field(
        index=True,
        foreign_key="document_sources.id",
        description="Parent DocumentSource (for fast LGA/jurisdiction queries)",
    )

    from_state: str = Field(description="State before the transition")
    to_state: str = Field(description="State after the transition")

    triggered_by: str = Field(
        description=(
            "What caused the transition: "
            "'monitor_run', 'etl_pipeline', 'api', 'bootstrap'"
        )
    )

    http_status: Optional[int] = Field(
        default=None,
        description="HTTP status code observed (populated for url_dead transitions)",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="MonitoringLog.run_id if triggered by a monitor run",
    )
    details: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional context (e.g. replacement URL, error message)",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        description="When this transition occurred",
    )
