"""Query service for RAG operations."""

from __future__ import annotations

import logging
import time
from typing import Optional

from sqlmodel import Session

from green_gov_rag.api.schemas.query import CoverageInfo, QueryResponse, SourceDocument
from green_gov_rag.api.services.cache import CacheService
from green_gov_rag.api.services.citation_verification import CitationVerificationService
from green_gov_rag.api.services.coverage_service import CoverageService
from green_gov_rag.api.services.regulatory_hierarchy import RegulatoryHierarchyService
from green_gov_rag.api.services.trust_score import TrustScoreService
from green_gov_rag.api.utils.citation_formatter import CitationFormatter
from green_gov_rag.config import settings
from green_gov_rag.models import QueryHistory
from green_gov_rag.models.base import engine
from green_gov_rag.rag.agent_tools import RAGAgent
from green_gov_rag.types import TOPIC_MAPPING, AustralianState

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

        # Initialize regulatory hierarchy service
        self.hierarchy_service = RegulatoryHierarchyService()

        # Initialize trust score service
        self.trust_service = TrustScoreService()

        # Initialize coverage service
        self.coverage_service = CoverageService()

    async def execute_query(
        self,
        query: str,
        region: Optional[str] = None,
        lgas: Optional[list[str]] = None,
        jurisdiction: Optional[str] = None,
        topics: Optional[list[str]] = None,
        max_sources: int = 5,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> QueryResponse:
        """Execute RAG query with caching.

        Args:
            query: User query
            region: Region filter (state/territory or LGA name)
            lgas: LGA names list (takes priority over region)
            jurisdiction: Jurisdiction filter
            topics: Topic filters
            max_sources: Maximum source documents
            session_id: Browser session ID for user-specific query history

        Returns:
            QueryResponse: Query response with answer and sources
        """
        start_time = time.time()

        # Normalize region abbreviation to full name using AustralianState enum
        normalized_region = None
        if region:
            try:
                # Try to parse as state abbreviation (e.g., 'SA' -> 'South Australia')
                state = AustralianState.from_name(region)
                normalized_region = state.full_name
            except ValueError:
                # If not a valid state, use the region as-is (could be LGA name)
                normalized_region = region

        # Normalize jurisdiction to lowercase (data stores: federal, state, local)
        normalized_jurisdiction = None
        if jurisdiction:
            normalized_jurisdiction = jurisdiction.lower()

        # Normalize topics - map user-friendly names to internal topic codes
        normalized_topics = None
        if topics:
            # Collect all mapped topics
            mapped_topics = []
            for user_topic in topics:
                topic_key = user_topic.lower()
                if topic_key in TOPIC_MAPPING:
                    # Use the mapping
                    mapped_topics.extend(TOPIC_MAPPING[topic_key])
                else:
                    # If no mapping, use as-is with underscores (might be exact match)
                    mapped_topics.append(topic_key.replace(" ", "_"))
            # Remove duplicates
            normalized_topics = list(set(mapped_topics)) if mapped_topics else None

        # Normalize LGAs - handle conflicts with region filter (Option B: Use LGAs, log warning)
        normalized_lgas = None
        if lgas:
            # Normalize LGA names - try both with and without common prefixes
            # Data in Qdrant may have "City of Adelaide" while user selects "Adelaide"
            normalized_lgas = []
            for lga in lgas:
                lga_clean = lga.strip()
                # Add both the original name and variants with common prefixes
                variants = [lga_clean]

                # If the name doesn't have a prefix, add variants with prefixes
                has_prefix = any(
                    lga_clean.startswith(p)
                    for p in ["City of ", "Shire of ", "Town of ", "District of "]
                )
                if not has_prefix:
                    variants.extend(
                        [
                            f"City of {lga_clean}",
                            f"Shire of {lga_clean}",
                            f"Town of {lga_clean}",
                            f"District of {lga_clean}",
                        ]
                    )

                # Add all variants for OR matching
                normalized_lgas.extend(variants)

            # Check for conflict between region and lgas
            if normalized_region:
                # Log warning if user specified both region and LGAs
                logger.warning(
                    f"Both region='{normalized_region}' and lgas={lgas} specified. "
                    f"Using LGA filter (takes priority). Both will be returned in filters_applied."
                )

        # Build metadata filters
        metadata_filters: dict[str, str | list[str]] = {}
        # LGAs take priority over region for filtering
        if normalized_lgas:
            metadata_filters["lga_names"] = normalized_lgas
            # Also include region in filters_applied for transparency
            if normalized_region:
                metadata_filters["region_specified"] = normalized_region
        elif normalized_region:
            # No LGAs specified, use region filter
            metadata_filters["region"] = normalized_region

        if normalized_jurisdiction:
            metadata_filters["jurisdiction"] = normalized_jurisdiction
        if normalized_topics:
            metadata_filters["topic"] = (
                normalized_topics[0]
                if len(normalized_topics) == 1
                else normalized_topics
            )

        # Phase 1: Retrieve documents (always happens)
        context, sources = self.rag_agent.retrieve(
            query=query, metadata_filters=metadata_filters or None, k=max_sources
        )

        # Phase 2: Check cache before expensive LLM generation
        cache_hit = False
        if self.cache_service:
            cache_key = self.cache_service._create_cache_key(
                query=query, context=context, filters=metadata_filters or None
            )

            cached_answer = await self.cache_service.get(cache_key, query=query)
            if cached_answer:
                logger.info(f"Cache hit for query: {query[:50]}...")
                answer = cached_answer
                cache_hit = True  # noqa: F841
            else:
                logger.info(f"Cache miss for query: {query[:50]}...")
                # Phase 3: Generate answer (cache miss only)
                answer = self.rag_agent.generate(query=query, context=context)

                # Store in cache with source document IDs
                source_ids = [
                    s.metadata.get("id") or s.metadata.get("title", "")
                    for s in sources
                    if hasattr(s, "metadata")
                ]
                await self.cache_service.set(
                    key=cache_key,
                    value=answer,
                    query=query,  # Pass query for semantic caching
                    source_documents=source_ids,
                )
        else:
            # No caching - direct generation
            answer = self.rag_agent.generate(query=query, context=context)

        # Convert sources to schema with citation enrichment
        source_docs = []
        for src in sources[:max_sources]:
            # Handle both Document objects and dict sources
            if hasattr(src, "metadata"):
                # LangChain Document object
                metadata = src.metadata
                page_content = src.page_content
                title = metadata.get("title", "Unknown")
                source_url = metadata.get("source_url", "")
                source_pdf_url = metadata.get("source_pdf_url")
                excerpt = page_content[:500] if page_content else None
            else:
                # Dict format (legacy)
                metadata = src.get("metadata", {})
                title = src.get("title", metadata.get("title", "Unknown"))
                source_url = src.get("source_url", metadata.get("source_url", ""))
                source_pdf_url = metadata.get("source_pdf_url")
                excerpt = src.get("excerpt", src.get("content", ""))

            # Extract metadata
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
                title=title,
                page_number=page_number,
                section_title=section_title,
                clause_reference=clause_reference,
                regulator=regulator,
            )

            # Build deep link using source_pdf_url (actual PDF) if available, fallback to source_url
            section_id = CitationFormatter.extract_section_id(
                section_hierarchy, clause_reference
            )
            deep_link = CitationFormatter.build_deep_link(
                source_url=source_pdf_url
                or source_url,  # Prefer source_pdf_url for direct PDF links
                page_number=page_number,
                section_id=section_id,
            )

            # Build page range if available
            page_range = metadata.get("page_range")
            if not page_range and page_number:
                # Fallback: single page range if not tracked in metadata
                page_range = [page_number, page_number]

            # Create enriched source document
            source_doc = SourceDocument(
                # Core fields
                title=title,
                source_url=source_url,
                excerpt=excerpt,
                relevance_score=metadata.get("score"),
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

        # Phase 3: Calculate trust score and detect conflicts
        trust_score = None
        trust_confidence = None
        trust_breakdown = None
        conflicts_detected = None
        hierarchy_explanation = None
        citation_warnings_list = []
        verification_results = None

        # Verify citations if enabled
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
                    if result.warning:
                        citation_warnings_list.append(result.warning)
                    if result.is_superseded:
                        citation_warnings_list.append(
                            f"Document {result.document_id}: v{result.cited_version} superseded by v{result.current_version}"
                        )

            except Exception as e:
                logger.error(f"Citation verification failed: {e}", exc_info=True)

        # Detect regulatory conflicts
        conflicts = None
        source_dicts = []
        try:
            source_dicts = [doc.model_dump() for doc in source_docs]
            conflicts = await self.hierarchy_service.detect_conflicts(source_dicts)

            if conflicts:
                conflicts_detected = [
                    {
                        "type": c.conflict_type,
                        "severity": c.severity,
                        "resolution": c.resolution,
                        "details": c.details,
                    }
                    for c in conflicts
                ]

            # Generate hierarchy explanation
            hierarchy_explanation = (
                self.hierarchy_service.generate_hierarchy_explanation(source_dicts)
            )

        except Exception as e:
            logger.error(f"Conflict detection failed: {e}", exc_info=True)
            # Re-build source_dicts if it failed
            if not source_dicts:
                source_dicts = [doc.model_dump() for doc in source_docs]

        # Calculate trust score
        try:
            # Calculate authority scores for each source
            authority_scores = {}
            for i, source_dict in enumerate(source_dicts):
                authority_scores[
                    f"source_{i}"
                ] = self.hierarchy_service.calculate_source_authority_score(source_dict)

            # Calculate composite trust score
            trust_breakdown_obj = self.trust_service.calculate_trust_score(
                citation_results=verification_results,
                sources=source_dicts,
                conflicts=conflicts if conflicts else None,
                authority_scores=authority_scores,
            )

            trust_score = trust_breakdown_obj.overall_score
            trust_confidence = trust_breakdown_obj.confidence_level
            trust_breakdown = {
                "citation_score": trust_breakdown_obj.citation_score,
                "authority_score": trust_breakdown_obj.authority_score,
                "conflict_score": trust_breakdown_obj.conflict_score,
                "accuracy_score": trust_breakdown_obj.accuracy_score,
                "warnings": trust_breakdown_obj.warnings,
            }

        except Exception as e:
            logger.error(f"Trust score calculation failed: {e}", exc_info=True)

        # Save to query history and get query_id
        query_id = self._save_query_history(
            query=query,
            answer=answer,
            region_filter=region,
            jurisdiction_filter=jurisdiction,
            topic_filter=",".join(topics) if topics else None,
            metadata_filters=metadata_filters,
            sources=sources[:max_sources],
            response_time_ms=response_time,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
        )

        # Calculate coverage info if region filter is provided
        coverage_info: Optional[CoverageInfo] = None
        if region:
            # Extract LGA code and name from region or metadata
            lga_code, lga_name = self._extract_lga_info(region, source_docs)
            coverage_info = self.coverage_service.get_lga_coverage(
                lga_code=lga_code,
                lga_name=lga_name,
            )

        return QueryResponse(
            query=query,
            answer=answer,
            sources=source_docs,
            filters_applied=metadata_filters,
            response_time_ms=response_time,
            query_id=query_id,  # Include query_id for feedback
            coverage_info=coverage_info,  # LGA coverage information
            # Phase 3 fields
            trust_score=trust_score,
            trust_confidence=trust_confidence,
            trust_breakdown=trust_breakdown,
            conflicts_detected=conflicts_detected,
            hierarchy_explanation=hierarchy_explanation,
            citation_warnings=citation_warnings_list
            if citation_warnings_list
            else None,
        )

    def _extract_lga_info(
        self, region: str, source_docs: list[SourceDocument]
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract LGA code and name from region filter or source documents.

        Args:
            region: Region filter string
            source_docs: List of source documents

        Returns:
            Tuple of (lga_code, lga_name)
        """
        # Try to extract from source documents' spatial metadata
        for doc in source_docs:
            if doc.spatial_metadata:
                lga_codes = doc.spatial_metadata.get("lga_codes", [])
                lga_names = doc.spatial_metadata.get("lga_names", [])
                if lga_codes and lga_names:
                    # Ensure lga_code is string (might be int in data)
                    lga_code = str(lga_codes[0]) if lga_codes[0] is not None else None
                    return lga_code, lga_names[0]

        # Fallback: use region as LGA name
        return None, region

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
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> Optional[int]:
        """Save query to history.

        Args:
            session_id: Browser session ID for user-specific query history
            ip_address: Client IP address (anonymized)
            user_agent: Client user agent string
            referer: HTTP referer header

        Returns:
            Query ID if successful, None otherwise
        """
        try:
            # Convert Document objects to serializable dicts
            sources_serializable = []
            for src in sources:
                if hasattr(src, "metadata") and hasattr(src, "page_content"):
                    # LangChain Document object - convert to dict
                    sources_serializable.append(
                        {
                            "content": src.page_content,
                            "metadata": src.metadata,
                        }
                    )
                elif isinstance(src, dict):
                    # Already a dict
                    sources_serializable.append(src)
                else:
                    # Unknown type - convert to string
                    logger.warning(
                        f"Unknown source type: {type(src)}, converting to string"
                    )
                    sources_serializable.append({"content": str(src)})

            with Session(engine) as session:
                history = QueryHistory(
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    referer=referer,
                    query_text=query,
                    answer=answer,
                    region_filter=region_filter,
                    jurisdiction_filter=jurisdiction_filter,
                    topic_filter=topic_filter,
                    metadata_filters=metadata_filters,
                    source_documents=sources_serializable,
                    source_count=len(sources_serializable),
                    response_time_ms=response_time_ms,
                )
                session.add(history)
                session.commit()
                session.refresh(history)
                return history.id
        except Exception as e:
            # Log error but don't fail the request
            logger.error("Failed to save query history: %s", e, exc_info=True)
            return None

    async def submit_feedback(
        self,
        query_id: int,
        rating: int,
        feedback_text: Optional[str] = None,
    ) -> bool:
        """Submit feedback for a query.

        Args:
            query_id: Query history ID
            rating: Rating from 1-5
            feedback_text: Optional feedback text

        Returns:
            True if successful, False if query not found
        """
        try:
            with Session(engine) as session:
                # Find the query
                query = session.get(QueryHistory, query_id)
                if not query:
                    logger.warning(f"Query not found: {query_id}")
                    return False

                # Update feedback fields
                query.feedback_rating = rating
                query.feedback_text = feedback_text

                session.add(query)
                session.commit()

                logger.info(f"Feedback submitted for query {query_id}: rating={rating}")
                return True

        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}", exc_info=True)
            return False
