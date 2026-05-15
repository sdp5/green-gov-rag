"""Normalized document models: sources → files → chunks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.hybrid import hybrid_property
from sqlmodel import JSON, Column, Field, SQLModel

from green_gov_rag.types import NEEDS_ATTENTION_THRESHOLD

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

    class Config:
        """Model configuration."""

        ignored_types = (hybrid_property,)
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

    # --- Hybrid properties: spatial_metadata accessors ---

    @hybrid_property
    def state_code(self) -> str | None:
        """Extract state from spatial_metadata JSON."""
        if not self.spatial_metadata:
            return None
        return self.spatial_metadata.get("state")

    @hybrid_property
    def source_lga_names(self) -> list[str]:
        """Extract lga_names from spatial_metadata JSON."""
        if not self.spatial_metadata:
            return []
        return self.spatial_metadata.get("lga_names", [])

    @hybrid_property
    def source_lga_codes(self) -> list[int]:
        """Extract lga_codes from spatial_metadata JSON."""
        if not self.spatial_metadata:
            return []
        return self.spatial_metadata.get("lga_codes", [])

    @hybrid_property
    def applies_to_all_lgas(self) -> bool:
        """Whether this source applies to all LGAs (federal/state scope)."""
        if not self.spatial_metadata:
            return False
        return self.spatial_metadata.get("applies_to_all_lgas", False)


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

    # --- Hybrid properties: error_message JSON accessors ---

    def _parse_error_data(self) -> dict | None:
        """Parse structured JSON from error_message field."""
        if not self.error_message:
            return None
        try:
            return json.loads(self.error_message)
        except (json.JSONDecodeError, TypeError):
            return None

    @hybrid_property
    def failure_reason(self) -> str | None:
        """Extract failure_reason from structured JSON error_message."""
        data = self._parse_error_data()
        if data is None:
            return "legacy" if self.error_message else None
        return data.get("failure_reason")

    @hybrid_property
    def attempt_count(self) -> int:
        """Extract cumulative attempt count from error_message JSON."""
        data = self._parse_error_data()
        if data is None:
            return 0
        return data.get("attempt_count", 0)

    @hybrid_property
    def needs_attention(self) -> bool:
        """True if 3+ consecutive failures with same reason."""
        if self.status != "download_failed":
            return False
        data = self._parse_error_data()
        if data is None:
            return False
        history = data.get("attempt_history", [])
        if len(history) < NEEDS_ATTENTION_THRESHOLD:
            return False
        recent = [h.get("reason") for h in history[-NEEDS_ATTENTION_THRESHOLD:]]
        return len(set(recent)) == 1

    @hybrid_property
    def last_attempt_at(self) -> str | None:
        """Extract last_attempt_at from error_message JSON."""
        data = self._parse_error_data()
        if data is None:
            return None
        return data.get("last_attempt_at")

    class Config:
        """Model configuration."""

        ignored_types = (hybrid_property,)
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
