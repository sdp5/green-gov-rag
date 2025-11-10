"""Chunk metadata model for vector embeddings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class Chunk(SQLModel, table=True):
    """Text chunk metadata (embeddings stored in FAISS/Qdrant).

    Each chunk references both:
    - source_id: The logical document source (config entry)
    - file_id: The specific file this chunk came from

    This allows tracking which PDF a chunk originated from while maintaining
    source-level context.
    """

    __tablename__ = "document_chunks"

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign keys
    source_id: str = Field(
        foreign_key="document_sources.id",
        index=True,
        description="Parent document source (config entry)",
    )
    file_id: str = Field(
        foreign_key="document_files.id",
        index=True,
        description="Specific file this chunk came from",
    )

    # Chunk details
    chunk_index: int = Field(description="Chunk position in document")
    text: str = Field(description="Chunk text content")

    # Chunk metadata
    char_count: int = Field(default=0, description="Character count")
    token_count: Optional[int] = Field(default=None, description="Token count")

    # Page/section info
    page_number: Optional[int] = Field(default=None, description="Page number if PDF")
    page_range: Optional[list[int]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Page range if chunk spans multiple pages [start, end]",
    )
    section_title: Optional[str] = Field(default=None, description="Section title")
    section_hierarchy: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Full section hierarchy from document root to current section",
    )
    clause_reference: Optional[str] = Field(
        default=None,
        description="Legal clause/section reference (e.g., 's.3.2.1', 'cl.42')",
    )

    # Deep linking and citation
    source_pdf_url: Optional[str] = Field(
        default=None,
        description="Direct PDF URL (from download_urls) for deep linking",
    )
    deep_link: Optional[str] = Field(
        default=None,
        description="Deep link to specific section/page in source document",
    )
    citation: Optional[str] = Field(
        default=None,
        description="Formatted citation string for display",
    )

    # Embedding info
    embedding_index: Optional[int] = Field(
        default=None,
        description="Index in FAISS vector store",
    )
    embedding_model: Optional[str] = Field(
        default=None,
        description="Embedding model used",
    )

    # Additional metadata
    metadata_: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional chunk metadata",
    )

    # Timestamp
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "source_id": "ncc_2022",
                "file_id": "ncc_2022_vol1",
                "chunk_index": 0,
                "text": "This is the first chunk...",
                "char_count": 512,
                "page_number": 1,
                "embedding_index": 0,
            }
        }
