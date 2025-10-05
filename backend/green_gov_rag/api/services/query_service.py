"""Query service for RAG operations."""

from __future__ import annotations

import time
from typing import Optional

from sqlmodel import Session

from green_gov_rag.api.schemas.query import QueryResponse, SourceDocument
from green_gov_rag.models import QueryHistory
from green_gov_rag.models.base import engine
from green_gov_rag.rag.agent_tools import RAGAgent


class QueryService:
    """Service for handling RAG queries."""

    def __init__(self):
        """Initialize query service."""
        self.rag_agent = RAGAgent()

    def execute_query(
        self,
        query: str,
        region: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        topics: Optional[list[str]] = None,
        max_sources: int = 5,
    ) -> QueryResponse:
        """Execute RAG query.

        Args:
            query: User query
            region: Region filter
            jurisdiction: Jurisdiction filter
            topics: Topic filters
            max_sources: Maximum source documents

        Returns:
            QueryResponse: Query response with answer and sources
        """
        start_time = time.time()

        # Build metadata filters
        metadata_filters: dict[str, str | list[str]] = {}
        if region:
            metadata_filters["region"] = region
        if jurisdiction:
            metadata_filters["jurisdiction"] = jurisdiction
        if topics:
            metadata_filters["topic"] = topics[0] if len(topics) == 1 else topics

        # Execute query
        answer, sources = self.rag_agent.query(
            query, metadata_filters=metadata_filters or None
        )

        # Convert sources to schema
        source_docs = [
            SourceDocument(
                title=src.get("title", "Unknown"),
                source_url=src.get("source_url", ""),
                excerpt=src.get("excerpt"),
                relevance_score=src.get("score"),
            )
            for src in sources[:max_sources]
        ]

        # Calculate response time
        response_time = (time.time() - start_time) * 1000

        # Save to query history
        self._save_query_history(
            query=query,
            answer=answer,
            region_filter=region,
            jurisdiction_filter=jurisdiction,
            topic_filter=",".join(topics) if topics else None,
            metadata_filters=metadata_filters,
            sources=sources[:max_sources],
            response_time_ms=response_time,
        )

        return QueryResponse(
            query=query,
            answer=answer,
            sources=source_docs,
            filters_applied=metadata_filters,
            response_time_ms=response_time,
        )

    def _save_query_history(
        self,
        query: str,
        answer: str,
        region_filter: Optional[str],
        jurisdiction_filter: Optional[str],
        topic_filter: Optional[str],
        metadata_filters: dict,
        sources: list,
        response_time_ms: float,
    ) -> None:
        """Save query to history."""
        try:
            with Session(engine) as session:
                history = QueryHistory(
                    query_text=query,
                    answer=answer,
                    region_filter=region_filter,
                    jurisdiction_filter=jurisdiction_filter,
                    topic_filter=topic_filter,
                    metadata_filters=metadata_filters,
                    source_documents=sources,
                    source_count=len(sources),
                    response_time_ms=response_time_ms,
                )
                session.add(history)
                session.commit()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to save query history: {e}")
