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


# --- Download failure tracking schemas ---


class DownloadFailureGroup(BaseModel):
    """A group of failures by a dimension (reason/state/lga/jurisdiction)."""

    group_key: str = Field(..., json_schema_extra={"examples": ["cloudflare"]})
    group_label: str = Field(
        ..., json_schema_extra={"examples": ["Cloudflare Protection"]}
    )
    count: int = Field(..., json_schema_extra={"examples": [20]})
    needs_attention_count: int = Field(..., json_schema_extra={"examples": [15]})
    sample_urls: list[str] = Field(
        default_factory=list,
        json_schema_extra={"examples": [["https://plan.sa.gov.au/doc.pdf"]]},
    )


class DownloadFailureSummaryResponse(BaseModel):
    """Failures grouped by a dimension."""

    group_by: str = Field(..., json_schema_extra={"examples": ["reason"]})
    total_failures: int = Field(..., json_schema_extra={"examples": [25]})
    total_needs_attention: int = Field(..., json_schema_extra={"examples": [20]})
    groups: list[DownloadFailureGroup]


class DownloadFailureItem(BaseModel):
    """Single failure detail with source context."""

    file_id: str = Field(..., json_schema_extra={"examples": ["abc123_def456"]})
    source_id: str = Field(..., json_schema_extra={"examples": ["abc123"]})
    source_title: str = Field(..., json_schema_extra={"examples": ["SA Planning Code"]})
    file_url: str = Field(
        ...,
        json_schema_extra={"examples": ["https://plan.sa.gov.au/doc.pdf"]},
    )
    failure_reason: str | None = Field(
        None, json_schema_extra={"examples": ["cloudflare"]}
    )
    attempt_count: int = Field(..., json_schema_extra={"examples": [3]})
    needs_attention: bool = Field(..., json_schema_extra={"examples": [True]})
    last_attempt_at: str | None = Field(
        None, json_schema_extra={"examples": ["2026-04-05T10:30:00Z"]}
    )
    status_code: int | None = Field(None, json_schema_extra={"examples": [403]})
    jurisdiction: str = Field(..., json_schema_extra={"examples": ["state"]})
    state: str | None = Field(None, json_schema_extra={"examples": ["SA"]})
    lga_names: list[str] = Field(
        default_factory=list,
        json_schema_extra={"examples": [["City of Adelaide"]]},
    )


class DownloadFailureListResponse(BaseModel):
    """Paginated failure list."""

    total: int = Field(..., json_schema_extra={"examples": [25]})
    failures: list[DownloadFailureItem]
