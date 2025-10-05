"""Query request/response schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """Source document reference."""

    title: str
    source_url: str
    excerpt: Optional[str] = None
    relevance_score: Optional[float] = None


class QueryRequest(BaseModel):
    """Query request schema."""

    query: str = Field(..., min_length=1, description="User query")
    region: Optional[str] = Field(None, description="Region filter")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction filter")
    topics: Optional[list[str]] = Field(None, description="Topic filters")
    max_sources: int = Field(5, ge=1, le=20, description="Max source documents")

    class Config:
        """Schema config."""

        json_schema_extra = {
            "example": {
                "query": "What are the emissions targets for NSW?",
                "region": "NSW",
                "jurisdiction": "State",
                "topics": ["Climate", "Emissions"],
                "max_sources": 5,
            }
        }


class QueryResponse(BaseModel):
    """Query response schema."""

    query: str
    answer: str
    sources: list[SourceDocument]
    filters_applied: dict
    response_time_ms: Optional[float] = None

    class Config:
        """Schema config."""

        json_schema_extra = {
            "example": {
                "query": "What are the emissions targets?",
                "answer": "The emissions targets are...",
                "sources": [
                    {
                        "title": "Climate Policy 2024",
                        "source_url": "https://example.gov/policy",
                        "excerpt": "Target of net zero by 2050...",
                    }
                ],
                "filters_applied": {"region": "NSW"},
                "response_time_ms": 1234.56,
            }
        }
