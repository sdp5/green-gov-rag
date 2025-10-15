"""Query service for RAG operations."""

from __future__ import annotations

import logging
import time
from typing import Optional

from sqlmodel import Session

from green_gov_rag.api.schemas.query import QueryResponse, SourceDocument
from green_gov_rag.api.services.cache import CacheService
from green_gov_rag.api.services.citation_verification import CitationVerificationService
from green_gov_rag.api.utils.citation_formatter import CitationFormatter
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

        # Initialize citation verification service
        self.citation_service = None
        if settings.enable_citation_verification:
            self.citation_service = CitationVerificationService(
                staleness_threshold_days=settings.citation_staleness_threshold_days
            )
            logger.info("Citation verification enabled")

    async def execute_query(
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

        # Convert sources to schema with citation enrichment
        source_docs = []
        for src in sources[:max_sources]:
            # Extract metadata
            metadata = src.get("metadata", {})
            esg_metadata = metadata.get("esg_metadata")
            spatial_metadata = metadata.get("spatial_metadata")

            # Build citation fields
            page_number = metadata.get("page_number")
            section_title = metadata.get("section_title")
            section_hierarchy = metadata.get("section_hierarchy")
            clause_reference = metadata.get("clause_reference")

            # Format citation using utility
            regulator = esg_metadata.get("regulator") if esg_metadata else None
            citation = CitationFormatter.format_citation(
                title=src.get("title", "Unknown"),
                page_number=page_number,
                section_title=section_title,
                clause_reference=clause_reference,
                regulator=regulator,
            )

            # Build deep link
            section_id = CitationFormatter.extract_section_id(
                section_hierarchy, clause_reference
            )
            deep_link = CitationFormatter.build_deep_link(
                source_url=src.get("source_url", ""),
                page_number=page_number,
                section_id=section_id,
            )

            # Build page range if available
            page_range = None
            if page_number:
                # Check if chunk spans multiple pages
                # This would require tracking in the chunk metadata
                # For now, just use single page
                page_range = [page_number, page_number]

            # Create enriched source document
            source_doc = SourceDocument(
                # Core fields
                title=src.get("title", "Unknown"),
                source_url=src.get("source_url", ""),
                excerpt=src.get("excerpt"),
                relevance_score=src.get("score"),
                # Citation metadata
                page_number=page_number,
                page_range=page_range,
                section_title=section_title,
                section_hierarchy=section_hierarchy,
                clause_reference=clause_reference,
                deep_link=deep_link,
                citation=citation,
                # Document metadata
                jurisdiction=metadata.get("jurisdiction"),
                category=metadata.get("category"),
                topic=metadata.get("topic"),
                region=metadata.get("region"),
                # ESG & spatial metadata
                esg_metadata=esg_metadata,
                spatial_metadata=spatial_metadata,
            )

            source_docs.append(source_doc)

        # Calculate response time
        response_time = (time.time() - start_time) * 1000

        # Verify citations if enabled
        citation_warnings = []
        if self.citation_service:
            try:
                response_dict = {
                    "query": query,
                    "answer": answer,
                    "sources": [doc.model_dump() for doc in source_docs],
                }
                verification_results = (
                    await self.citation_service.verify_query_response(response_dict)
                )

                # Collect warnings
                for result in verification_results:
                    if result.warning or result.is_superseded:
                        citation_warnings.append(
                            {
                                "document_id": result.document_id,
                                "warning": result.warning,
                                "is_superseded": result.is_superseded,
                                "current_version": result.current_version,
                                "cited_version": result.cited_version,
                            }
                        )

                if citation_warnings:
                    logger.warning(
                        f"Citation warnings found for query: {len(citation_warnings)} issues"
                    )

            except Exception as e:
                logger.error(f"Citation verification failed: {e}", exc_info=True)

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
