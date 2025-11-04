"""Analytics service."""

from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Session, select

from green_gov_rag.api.schemas.analytics import (
    AnalyticsStats,
    DistributionData,
)
from green_gov_rag.models import DocumentSource, QueryHistory
from green_gov_rag.models.base import engine


class AnalyticsService:
    """Service for analytics and statistics."""

    def get_stats(self) -> AnalyticsStats:
        """Get overall analytics statistics.

        Returns:
            AnalyticsStats: Statistics and distributions
        """
        with Session(engine) as session:
            # Total documents
            total_docs = session.exec(
                select(func.count()).select_from(DocumentSource)
            ).one()

            # Total queries
            total_queries = session.exec(
                select(func.count()).select_from(QueryHistory)
            ).one()

            # Average response time (ms)
            avg_response = session.exec(
                select(func.avg(QueryHistory.response_time_ms))
            ).one()

            # Documents by jurisdiction
            jurisdiction_results = session.exec(
                select(DocumentSource.jurisdiction, func.count(DocumentSource.id))  # type: ignore[arg-type]
                .group_by(DocumentSource.jurisdiction)
                .order_by(func.count(DocumentSource.id).desc())  # type: ignore[arg-type]
            ).all()
            by_jurisdiction = [
                DistributionData(name=name, count=count)
                for name, count in jurisdiction_results
            ]

            # Documents by topic
            topic_results = session.exec(
                select(DocumentSource.topic, func.count(DocumentSource.id))  # type: ignore[arg-type]
                .group_by(DocumentSource.topic)
                .order_by(func.count(DocumentSource.id).desc())  # type: ignore[arg-type]
            ).all()
            by_topic = [
                DistributionData(name=name, count=count)
                for name, count in topic_results
            ]

            # Documents by region (excluding None)
            region_results = session.exec(
                select(DocumentSource.region, func.count(DocumentSource.id))  # type: ignore[arg-type]
                .where(DocumentSource.region.is_not(None))  # type: ignore[union-attr]
                .group_by(DocumentSource.region)
                .order_by(func.count(DocumentSource.id).desc())  # type: ignore[arg-type]
            ).all()
            by_region = [
                DistributionData(name=name or "Unknown", count=count)
                for name, count in region_results
            ]

            return AnalyticsStats(
                total_documents=total_docs,
                total_queries=total_queries,
                avg_response_time_ms=avg_response,
                documents_by_jurisdiction=by_jurisdiction,
                documents_by_topic=by_topic,
                documents_by_region=by_region,
            )
