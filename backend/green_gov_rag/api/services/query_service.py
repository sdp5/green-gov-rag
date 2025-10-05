"""Query service for RAG operations."""

from __future__ import annotations

import logging
import time
from typing import Optional

from sqlmodel import Session

from green_gov_rag.api.schemas.query import QueryResponse, SourceDocument
from green_gov_rag.api.services.cache import CacheService
from green_gov_rag.config import settings
from green_gov_rag.models import QueryHistory
from green_gov_rag.models.base import engine
from green_gov_rag.rag.agent_tools import RAGAgent

logger = logging.getLogger(__name__)


class QueryService:
    """Service for handling RAG queries."""

    def __init__(self):
        """Initialize query service."""
        self.rag_agent = RAGAgent()

        # Initialize cache service
        self.cache_service = None
        if settings.enable_cache:
            self.cache_service = CacheService(
                enable_redis=settings.enable_redis_cache,
                redis_host=settings.redis_host,
                redis_port=settings.redis_port,
                cache_ttl=settings.cache_ttl,
                enable_semantic=settings.enable_semantic_cache,
            )
            logger.info(
                "Cache enabled (Redis: %s, TTL: %ds)",
                settings.enable_redis_cache,
                settings.cache_ttl,
            )

    def execute_query(
        self,
        query: str,
        region: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        topics: Optional[list[str]] = None,
        max_sources: int = 5,
    ) -> QueryResponse:
        """Execute RAG query with caching.

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

        # Execute full RAG query (retrieval + generation)
        # TODO: Refactor RAGAgent to support caching at the generation step
        answer, sources = self.rag_agent.query(
            query, metadata_filters=metadata_filters or None
        )

        # Build context from sources for potential caching
        _ = self._build_context(sources[:max_sources])

        # Note: Caching temporarily disabled until RAGAgent refactored
        # TODO: Add caching support by exposing retrieval and generation methods separately

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

    def _build_context(self, sources: list[dict]) -> str:
        """Build context string from source documents.

        Args:
            sources: List of source documents

        Returns:
            Context string for LLM
        """
        context_parts = []
        for i, src in enumerate(sources, 1):
            context_parts.append(
                f"Source {i}:\n"
                f"Title: {src.get('title', 'Unknown')}\n"
                f"Content: {src.get('excerpt', src.get('content', ''))}\n"
            )
        return "\n".join(context_parts)

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
            logger.error("Failed to save query history: %s", e, exc_info=True)
