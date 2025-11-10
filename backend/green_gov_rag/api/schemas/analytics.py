"""Analytics schemas."""

from __future__ import annotations

from pydantic import BaseModel


class TopicDistribution(BaseModel):
    """Topic distribution data."""

    topic: str
    count: int


class DistributionData(BaseModel):
    """Distribution data (jurisdiction/region/topic)."""

    name: str
    count: int


class AnalyticsStats(BaseModel):
    """Analytics statistics."""

    total_documents: int
    total_queries: int
    avg_response_time_ms: float | None = None
    documents_by_jurisdiction: list[DistributionData]
    documents_by_topic: list[DistributionData]
    documents_by_region: list[DistributionData]
    recent_queries: int = 0
