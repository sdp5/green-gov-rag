"""Document version tracking model for monitoring updates."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class DocumentVersion(SQLModel, table=True):
    """Track document versions for change detection.

    This model stores version history for documents, enabling:
    - Detection of when documents are updated
    - Rollback to previous versions if needed
    - Audit trail of document changes
    - Citation verification against specific versions
    """

    __tablename__ = "document_versions"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    file_id: str = Field(
        index=True,
        foreign_key="document_files.id",
        description="Reference to specific document file",
    )
    source_id: str = Field(
        index=True,
        foreign_key="document_sources.id",
        description="Reference to parent document source",
    )

    # Version tracking
    version_number: int = Field(
        index=True,
        description="Sequential version number (1, 2, 3...)",
    )
    content_hash: str = Field(
        index=True,
        description="SHA256 hash of document content for change detection",
    )

    # Source information
    source_url: str = Field(description="URL where this version was retrieved")
    file_size_bytes: Optional[int] = Field(
        default=None,
        description="File size in bytes",
    )

    # Change detection metadata
    change_type: str = Field(
        index=True,
        description="Type of change: 'new', 'updated', 'unchanged'",
    )
    change_summary: Optional[str] = Field(
        default=None,
        description="Human-readable summary of changes",
    )
    confidence_score: float = Field(
        default=1.0,
        description="Confidence in change detection (0-1)",
    )

    # Timestamps
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this version was discovered",
    )
    downloaded_at: Optional[datetime] = Field(
        default=None,
        description="When this version was downloaded",
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="When this version was processed into chunks/embeddings",
    )

    # Remote metadata (from source website)
    remote_last_modified: Optional[datetime] = Field(
        default=None,
        description="Last-Modified header from remote server",
    )
    remote_etag: Optional[str] = Field(
        default=None,
        description="ETag header from remote server",
    )

    # Additional metadata (stored as JSON)
    metadata_: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional version metadata as JSON",
    )

    # Processing status
    status: str = Field(
        default="discovered",
        index=True,
        description="Status: discovered/downloading/processing/completed/failed",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed",
    )

    # Version lifecycle
    is_current: bool = Field(
        default=False,
        index=True,
        description="True if this is the current/latest version",
    )
    superseded_at: Optional[datetime] = Field(
        default=None,
        description="When this version was superseded by a newer version",
    )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "id": 1,
                "source_id": "cer_scope2_guideline",
                "version_number": 3,
                "content_hash": "a1b2c3d4e5f6...",
                "source_url": "https://cer.gov.au/scope2-guideline.pdf",
                "file_size_bytes": 1024000,
                "change_type": "updated",
                "change_summary": "Updated section 3.2.1 with new market-based accounting methods",
                "confidence_score": 0.95,
                "discovered_at": "2025-10-15T02:00:00Z",
                "remote_last_modified": "2025-10-14T18:30:00Z",
                "status": "completed",
                "is_current": True,
            }
        }


class MonitoringLog(SQLModel, table=True):
    """Log of monitoring runs for document sources.

    Tracks when monitoring jobs run, what they discover, and any errors.
    """

    __tablename__ = "monitoring_logs"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Source information
    source_type: str = Field(
        index=True,
        description="Document source type (e.g., 'cer_emissions')",
    )
    source_config_id: Optional[str] = Field(
        default=None,
        index=True,
        description="Specific config ID if source has multiple configs",
    )

    # Run information
    run_id: str = Field(
        index=True,
        description="Unique identifier for this monitoring run (UUID)",
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When monitoring started",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When monitoring completed",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Duration of monitoring run in seconds",
    )

    # Results
    documents_checked: int = Field(
        default=0,
        description="Number of documents checked for updates",
    )
    documents_discovered: int = Field(
        default=0,
        description="Number of new documents discovered",
    )
    documents_updated: int = Field(
        default=0,
        description="Number of updated documents found",
    )
    documents_unchanged: int = Field(
        default=0,
        description="Number of documents with no changes",
    )

    # Status
    status: str = Field(
        default="running",
        index=True,
        description="Status: running/completed/failed",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed",
    )

    # Additional details (stored as JSON)
    details: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional run details as JSON",
    )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "id": 1,
                "source_type": "cer_emissions",
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "started_at": "2025-10-15T02:00:00Z",
                "completed_at": "2025-10-15T02:05:30Z",
                "duration_seconds": 330.5,
                "documents_checked": 25,
                "documents_discovered": 2,
                "documents_updated": 3,
                "documents_unchanged": 20,
                "status": "completed",
            }
        }
