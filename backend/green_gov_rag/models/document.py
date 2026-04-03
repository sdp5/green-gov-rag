"""Normalized document models: sources → files → chunks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import JSON, Column, Field, SQLModel

if TYPE_CHECKING:
    pass  # Relationships will be defined inline


class DocumentSource(SQLModel, table=True):
    """Document source from config (e.g., one config entry with multiple PDFs).

    Represents a logical document source that may contain multiple files.
    Maps 1:1 with entries in documents_config.yml.

    Example: "National Construction Code (NCC)" is one source with 4 PDF files.
    """

    __tablename__ = "document_sources"

    # Primary key
    id: str = Field(primary_key=True, description="Unique source identifier")

    # Basic metadata
    title: str = Field(index=True, description="Source title")
    source_url: str = Field(description="Source website URL (homepage)")

    # Classification fields
    jurisdiction: str = Field(index=True, description="Federal/State/Local")
    topic: str = Field(index=True, description="Document topic/category")
    region: Optional[str] = Field(
        default=None, index=True, description="Geographic region"
    )
    category: Optional[str] = Field(
        default=None, index=True, description="Document category"
    )

    # Additional metadata (stored as JSON)
    metadata_: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional metadata as JSON",
    )

    # ESG-specific metadata
    esg_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="ESG/emissions metadata (frameworks, scopes, gases, etc.)",
    )

    # Spatial/geographic metadata
    spatial_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Spatial metadata (LGA codes, state, spatial scope, etc.)",
    )

    # Processing status
    status: str = Field(
        default="pending",
        index=True,
        description="Processing status: pending/processing/completed/failed",
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="Processing completion timestamp",
    )

    # Aggregated stats (across all files)
    file_count: int = Field(default=0, description="Number of files in this source")
    chunk_count: int = Field(default=0, description="Total chunks across all files")
    embedding_model: Optional[str] = Field(
        default=None,
        description="Embedding model used",
    )

    # Lifecycle / registry tracking
    db_bootstrapped_at: Optional[datetime] = Field(
        default=None,
        description="When this source was first seeded from YAML into the DB",
    )
    last_monitored_at: Optional[datetime] = Field(
        default=None,
        description="When monitoring last ran for this source",
    )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "id": "ncc_2022",
                "title": "National Construction Code (NCC) 2022",
                "source_url": "https://ncc.abcb.gov.au/",
                "jurisdiction": "federal",
                "category": "building",
                "topic": "standards",
                "region": "Australia",
                "status": "completed",
                "file_count": 4,
                "chunk_count": 36170,
            }
        }


class DocumentFile(SQLModel, table=True):
    """Individual document file (e.g., one PDF from a source).

    Represents a single physical file that was downloaded.
    Many-to-one relationship with DocumentSource.

    Example: "ncc2022-volume-one.pdf" is one file of the NCC source.
    """

    __tablename__ = "document_files"

    # Primary key
    id: str = Field(primary_key=True, description="Unique file identifier")

    # Foreign key to source
    source_id: str = Field(
        foreign_key="document_sources.id",
        index=True,
        description="Parent source ID",
    )

    # File information
    filename: str = Field(index=True, description="Original filename")
    file_url: str = Field(description="Direct download URL for this file")
    content_hash: str = Field(
        index=True,
        description="SHA256 hash of file content for change detection",
    )
    file_size_bytes: Optional[int] = Field(
        default=None,
        description="File size in bytes",
    )

    # File-specific metadata
    file_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="File-specific metadata (page count, format, etc.)",
    )

    # Processing status
    status: str = Field(
        default="pending",
        index=True,
        description="Status: pending/downloading/processing/completed/failed",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed",
    )

    # Timestamps
    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this file was discovered",
    )
    downloaded_at: Optional[datetime] = Field(
        default=None,
        description="When file was downloaded",
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="When file was processed into chunks",
    )

    # Processing stats
    chunk_count: int = Field(default=0, description="Number of chunks from this file")

    # Lifecycle tracking
    lifecycle_state: str = Field(
        default="detect",
        index=True,
        description=(
            "Document lifecycle state: detect/fetch/chunk/embed/"
            "available_for_search/url_dead/mark_superseded/removed_from_search"
        ),
    )
    lifecycle_transitioned_at: Optional[datetime] = Field(
        default=None,
        description="When lifecycle_state last changed",
    )
    superseded_by_url: Optional[str] = Field(
        default=None,
        description="Replacement URL provided by admin when this file is superseded",
    )
    http_last_checked_at: Optional[datetime] = Field(
        default=None,
        description="When the URL was last checked for availability",
    )
    http_status_code: Optional[int] = Field(
        default=None,
        description="Last HTTP status code seen when checking the URL",
    )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "id": "ncc_2022_vol1",
                "source_id": "ncc_2022",
                "filename": "ncc2022-volume-one.pdf",
                "file_url": "https://ncc.abcb.gov.au/system/files/ncc/ncc2022-volume-one.pdf",
                "content_hash": "a1b2c3d4e5f6...",
                "file_size_bytes": 15728640,
                "status": "completed",
                "chunk_count": 8543,
            }
        }
