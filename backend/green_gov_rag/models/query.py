"""Query history model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class QueryHistory(SQLModel, table=True):
    """Query history for analytics and tracking."""

    __tablename__ = "query_history"

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Query details
    query_text: str = Field(index=True, description="User query text")
    answer: str = Field(description="Generated answer")

    # Filters applied
    region_filter: Optional[str] = Field(default=None, description="Region filter")
    topic_filter: Optional[str] = Field(default=None, description="Topic filter")
    jurisdiction_filter: Optional[str] = Field(
        default=None,
        description="Jurisdiction filter",
    )

    # Metadata
    metadata_filters: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="All metadata filters applied",
    )

    # Sources
    source_documents: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Source documents used",
    )
    source_count: int = Field(default=0, description="Number of sources")

    # Performance metrics
    response_time_ms: Optional[float] = Field(
        default=None,
        description="Response time in milliseconds",
    )
    embedding_model: Optional[str] = Field(
        default=None,
        description="Embedding model used",
    )
    llm_model: Optional[str] = Field(default=None, description="LLM model used")

    # User feedback (optional)
    feedback_rating: Optional[int] = Field(
        default=None,
        description="User rating 1-5",
    )
    feedback_text: Optional[str] = Field(default=None, description="User feedback")

    # Timestamp
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="Query timestamp",
    )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "query_text": "What are the emissions targets for NSW?",
                "answer": "NSW has set a target...",
                "region_filter": "NSW",
                "topic_filter": "Climate",
                "source_count": 3,
                "response_time_ms": 1234.56,
            }
        }
