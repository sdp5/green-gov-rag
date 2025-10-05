"""Admin API response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    """Dashboard statistics response."""

    documents: dict[str, int] = Field(
        ...,
        json_schema_extra={
            "examples": [
                {
                    "total": 150,
                    "processing": 5,
                    "failed": 2,
                    "completed": 143,
                }
            ]
        },
    )
    queries: dict[str, int | list[dict]] = Field(
        ...,
        json_schema_extra={
            "examples": [
                {
                    "total": 1250,
                    "recent": [
                        {
                            "id": "q123",
                            "query_text": "What are emissions rules?",
                            "created_at": "2025-01-15T10:30:00",
                            "response_time_ms": 450,
                        }
                    ],
                }
            ]
        },
    )


class AdminDocumentItem(BaseModel):
    """Admin document list item."""

    id: str = Field(..., json_schema_extra={"examples": ["doc_abc123"]})
    title: str = Field(
        ..., json_schema_extra={"examples": ["NSW Emissions Guidelines"]}
    )
    jurisdiction: str | None = Field(None, json_schema_extra={"examples": ["NSW"]})
    status: str = Field(..., json_schema_extra={"examples": ["completed"]})
    created_at: str | None = Field(
        None, json_schema_extra={"examples": ["2025-01-15T10:30:00"]}
    )
    error_message: str | None = Field(None, json_schema_extra={"examples": [None]})


class AdminDocumentListResponse(BaseModel):
    """Admin document list response."""

    documents: list[AdminDocumentItem]


class AdminDocumentDetailResponse(BaseModel):
    """Admin document detail response."""

    id: str = Field(..., json_schema_extra={"examples": ["doc_abc123"]})
    title: str = Field(
        ..., json_schema_extra={"examples": ["NSW Emissions Guidelines"]}
    )
    source_url: str | None = Field(
        None, json_schema_extra={"examples": ["https://example.com/doc.pdf"]}
    )
    jurisdiction: str | None = Field(None, json_schema_extra={"examples": ["NSW"]})
    topic: str | None = Field(None, json_schema_extra={"examples": ["emissions"]})
    region: str | None = Field(None, json_schema_extra={"examples": ["NSW"]})
    status: str = Field(..., json_schema_extra={"examples": ["completed"]})
    error_message: str | None = Field(None, json_schema_extra={"examples": [None]})
    created_at: str | None = Field(
        None, json_schema_extra={"examples": ["2025-01-15T10:30:00"]}
    )
    updated_at: str | None = Field(
        None, json_schema_extra={"examples": ["2025-01-15T11:00:00"]}
    )


class AdminActionResponse(BaseModel):
    """Generic admin action response."""

    status: str = Field(..., json_schema_extra={"examples": ["triggered"]})
    document_id: str | None = Field(
        None, json_schema_extra={"examples": ["doc_abc123"]}
    )
    message: str | None = Field(
        None, json_schema_extra={"examples": ["Document reprocessing triggered"]}
    )


class QueryAnalyticsResponse(BaseModel):
    """Query analytics response."""

    period_days: int = Field(..., json_schema_extra={"examples": [7]})
    total_queries: int = Field(..., json_schema_extra={"examples": [1250]})
    avg_response_time_ms: float = Field(..., json_schema_extra={"examples": [425.5]})
    top_topics: list[dict[str, Any]] = Field(
        ...,
        json_schema_extra={
            "examples": [
                [
                    {"topic": "emissions", "count": 450},
                    {"topic": "biodiversity", "count": 320},
                ]
            ]
        },
    )


class SystemHealthResponse(BaseModel):
    """System health response."""

    database: str = Field(..., json_schema_extra={"examples": ["connected"]})
    vector_store: str = Field(..., json_schema_extra={"examples": ["faiss"]})
    llm_provider: str = Field(..., json_schema_extra={"examples": ["openai"]})
