"""Document metadata model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class Document(SQLModel, table=True):
    """Document metadata stored in database."""

    __tablename__ = "documents"

    # Primary key
    id: str = Field(primary_key=True, description="Unique document identifier")

    # Basic metadata
    title: str = Field(index=True, description="Document title")
    source_url: str = Field(description="Original source URL")
    source_pdf_url: Optional[str] = Field(
        default=None,
        description="Direct PDF URL (from download_urls) for deep linking",
    )

    # Classification fields
    jurisdiction: str = Field(index=True, description="Federal/State/Local")
    topic: str = Field(index=True, description="Document topic/category")
    region: Optional[str] = Field(
        default=None, index=True, description="Geographic region"
    )
    category: Optional[str] = Field(
        default=None, index=True, description="Document category"
    )

    # Content
    content: Optional[str] = Field(default=None, description="Full text content")
    summary: Optional[str] = Field(default=None, description="Document summary")

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
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="Processing completion timestamp",
    )

    # Embedding info
    chunk_count: int = Field(default=0, description="Number of chunks created")
    embedding_model: Optional[str] = Field(
        default=None,
        description="Embedding model used",
    )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "id": "doc_001",
                "title": "Environmental Policy 2024",
                "source_url": "https://example.gov/policy",
                "jurisdiction": "Federal",
                "topic": "Climate",
                "region": "NSW",
                "status": "completed",
                "chunk_count": 15,
            }
        }
