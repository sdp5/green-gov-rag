"""Pydantic schemas for document lifecycle management API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Summary / counts
# ---------------------------------------------------------------------------


class LifecycleSummary(BaseModel):
    """Counts of DocumentFiles in each lifecycle state."""

    detect: int = 0
    fetch: int = 0
    chunk: int = 0
    embed: int = 0
    available_for_search: int = 0
    url_dead: int = 0
    mark_superseded: int = 0
    removed_from_search: int = 0
    total_files: int = 0
    total_sources: int = 0
    last_monitoring_run: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Document file entry (for the registry table)
# ---------------------------------------------------------------------------


class LifecycleDocumentEntry(BaseModel):
    """One row in the LGA-grouped document registry table."""

    file_id: str
    source_id: str
    title: str
    jurisdiction: str
    topic: str
    lga_names: list[str]  # from spatial_metadata.lga_names
    applies_to_all_lgas: bool
    file_url: str
    lifecycle_state: str
    lifecycle_transitioned_at: Optional[datetime]
    http_status_code: Optional[int]
    http_last_checked_at: Optional[datetime]
    superseded_by_url: Optional[str]


class LifecycleDocumentListResponse(BaseModel):
    """Paginated response for the document registry table."""

    items: list[LifecycleDocumentEntry]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# LGA-grouped view
# ---------------------------------------------------------------------------


class LGADocumentGroup(BaseModel):
    """All documents for a single LGA (or 'All LGAs' for federal/state)."""

    lga_name: str  # e.g. "Adelaide City Council" or "All LGAs"
    documents: list[LifecycleDocumentEntry]


class LGALifecycleResponse(BaseModel):
    """LGA-grouped document registry response."""

    groups: list[LGADocumentGroup]
    total_lgas: int
    total_files: int


# ---------------------------------------------------------------------------
# Lifecycle event history
# ---------------------------------------------------------------------------


class LifecycleEventEntry(BaseModel):
    """One row from lifecycle_event_log."""

    id: int
    from_state: str
    to_state: str
    triggered_by: str
    http_status: Optional[int]
    run_id: Optional[str]
    details: Optional[dict]
    created_at: datetime


# ---------------------------------------------------------------------------
# Admin actions
# ---------------------------------------------------------------------------


class ReplaceDocumentRequest(BaseModel):
    """Admin provides a replacement URL for a url_dead document."""

    new_url: str  # validated as a URL string


class RegisterDocumentRequest(BaseModel):
    """Register a new document source via the API (no YAML PR needed)."""

    title: str
    source_url: str
    download_urls: list[str]
    jurisdiction: str
    category: str
    topic: str
    region: Optional[str] = None
    esg_metadata: Optional[dict] = None
    spatial_metadata: Optional[dict] = None


class RegisterDocumentResponse(BaseModel):
    """Response after registering a new document."""

    source_id: str
    file_ids: list[str]
    lifecycle_state: str = "detect"
    message: str
