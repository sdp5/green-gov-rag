"""Document schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Document response schema."""

    id: str
    title: str
    source_url: str
    jurisdiction: str
    topic: str
    region: Optional[str] = None
    category: Optional[str] = None
    status: str
    chunk_count: int
    created_at: datetime
    processed_at: Optional[datetime] = None


class DocumentsFilter(BaseModel):
    """Document filter parameters."""

    jurisdiction: Optional[str] = None
    topic: Optional[str] = None
    region: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


class DocumentListResponse(BaseModel):
    """Document list response."""

    documents: list[DocumentResponse]
    total: int
    limit: int
    offset: int
