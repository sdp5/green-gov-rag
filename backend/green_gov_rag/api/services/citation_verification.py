"""Citation verification service for ensuring RAG responses cite current versions.

This service verifies that:
1. Citations in RAG responses refer to current document versions
2. Quoted text matches the cited document version
3. Users are warned when citing superseded documents
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import desc
from sqlmodel import Session, col, select

from green_gov_rag.models import DocumentVersion
from green_gov_rag.models.base import engine

logger = logging.getLogger(__name__)


@dataclass
class CitationVerificationResult:
    """Result of citation verification check."""

    is_current: bool
    confidence: float  # 0-1, confidence in verification
    document_id: str
    cited_version: int | None
    current_version: int
    is_superseded: bool
    superseded_at: datetime | None
    quote_match: bool | None = None
    quote_match_score: float | None = None
    relevance_score: float | None = None  # 0-1, source relevance to answer
    warning: str | None = None
    details: str | None = None


@dataclass
class QuoteVerificationResult:
    """Result of verifying a quote against document content."""

    exact_match: bool
    similarity_score: float  # 0-1
    found_in_version: int | None
    snippet_context: str | None = None
    warning: str | None = None


class CitationVerificationService:
    """Service for verifying citations in RAG responses.

    Ensures that:
    - Citations reference current document versions
    - Quoted text matches the cited document
    - Users are warned about outdated citations
    """

    def __init__(self, staleness_threshold_days: int = 30):
        """Initialize citation verification service.

        Args:
            staleness_threshold_days: Days after which to warn about old citations
        """
        self.staleness_threshold_days = staleness_threshold_days

    async def verify_query_response(
        self,
        query_response: dict[str, Any],
        query: str | None = None,
        answer: str | None = None,
        max_sources: int = 3,
        skip_relevance: bool = False,
    ) -> list[CitationVerificationResult]:
        """Verify all citations in a query response.

        Args:
            query_response: QueryResponse dict with sources
            query: Original user query (for relevance checking)
            answer: Generated answer (for relevance checking)
            max_sources: Maximum number of sources to verify (default 3, saves LLM calls)
            skip_relevance: Skip expensive LLM-based relevance verification (default False)

        Returns:
            List of verification results for each citation
        """
        import asyncio

        sources = query_response.get("sources", [])

        # Limit to top N sources to reduce LLM costs
        sources_to_verify = sources[:max_sources]

        # Build list of verification tasks
        tasks = []
        for source in sources_to_verify:
            # Extract file identifier from chunk metadata
            file_id = self._extract_file_id(source)
            if not file_id:
                logger.warning(f"Could not extract file_id from source: {source}")
                continue

            # Create verification task
            task = self.verify_citation(
                file_id=file_id,
                excerpt=source.get("excerpt"),
                metadata=source,
                query=query,
                answer=answer,
                skip_relevance=skip_relevance,
            )
            tasks.append(task)

        # Run all verifications in parallel
        results = await asyncio.gather(*tasks)

        return results

    async def verify_citation(
        self,
        file_id: str,
        excerpt: str | None = None,
        metadata: dict[str, Any] | None = None,
        query: str | None = None,
        answer: str | None = None,
        skip_relevance: bool = False,
    ) -> CitationVerificationResult:
        """Verify a single citation references the current document version.

        Args:
            file_id: Document file identifier
            excerpt: Quoted text from the document
            metadata: Additional citation metadata
            query: Original user query (for relevance checking)
            answer: Generated answer (for relevance checking)
            skip_relevance: Skip expensive LLM-based relevance verification

        Returns:
            CitationVerificationResult with verification status
        """
        with Session(engine) as session:
            # Get all versions of this file
            statement = (
                select(DocumentVersion)
                .where(DocumentVersion.file_id == file_id)
                .order_by(desc(col(DocumentVersion.version_number)))
            )
            versions = session.exec(statement).all()

            if not versions:
                return CitationVerificationResult(
                    is_current=False,
                    confidence=0.0,
                    document_id=file_id,
                    cited_version=None,
                    current_version=0,
                    is_superseded=False,
                    superseded_at=None,
                    warning="Document not found in version tracking system",
                )

            # Get current version
            current_version = versions[0]

            # Check if citing a specific version
            cited_version_num = None
            if metadata:
                cited_version_num = metadata.get("version_number")

            # Verify quote if provided
            quote_match = None
            quote_match_score = None
            if excerpt:
                quote_result = await self._verify_quote(
                    excerpt, current_version, session
                )
                quote_match = quote_result.exact_match
                quote_match_score = quote_result.similarity_score

            # Verify relevance if answer is provided (skip if not needed to save LLM calls)
            relevance_score = None
            if excerpt and answer and not skip_relevance:
                relevance_score = await self._verify_relevance(
                    excerpt=excerpt,
                    query=query,
                    answer=answer,
                    metadata=metadata,
                )

            # Check if current version is the one being cited
            if cited_version_num:
                is_current = cited_version_num == current_version.version_number
                cited_version_obj = next(
                    (v for v in versions if v.version_number == cited_version_num),
                    None,
                )

                if not is_current and cited_version_obj:
                    # Citing an old version
                    return CitationVerificationResult(
                        is_current=False,
                        confidence=1.0,
                        document_id=file_id,
                        cited_version=cited_version_num,
                        current_version=current_version.version_number,
                        is_superseded=True,
                        superseded_at=cited_version_obj.superseded_at,
                        quote_match=quote_match,
                        quote_match_score=quote_match_score,
                        relevance_score=relevance_score,
                        warning=f"Citing outdated version {cited_version_num}. "
                        f"Current version is {current_version.version_number}.",
                    )

            # Check staleness (even if citing current version)
            warning = None
            if current_version.discovered_at:
                age_days = (
                    datetime.utcnow() - current_version.discovered_at
                ).total_seconds() / 86400

                if age_days > self.staleness_threshold_days:
                    warning = (
                        f"Citation may be stale. Last checked "
                        f"{int(age_days)} days ago. "
                        f"Consider re-checking source."
                    )

            return CitationVerificationResult(
                is_current=True,
                confidence=1.0 if quote_match else 0.8,
                document_id=file_id,
                cited_version=current_version.version_number,
                current_version=current_version.version_number,
                is_superseded=False,
                superseded_at=None,
                quote_match=quote_match,
                quote_match_score=quote_match_score,
                relevance_score=relevance_score,
                warning=warning,
            )

    async def check_citation_currency(
        self, file_id: str, last_checked: datetime | None = None
    ) -> dict[str, Any]:
        """Check if a citation is current or if document has been updated.

        Args:
            file_id: Document file identifier
            last_checked: When the citation was last verified

        Returns:
            Dictionary with currency status and update information
        """
        with Session(engine) as session:
            # Get current version
            statement = (
                select(DocumentVersion)
                .where(DocumentVersion.file_id == file_id)
                .where(DocumentVersion.is_current == True)  # noqa: E712
            )
            current_version = session.exec(statement).first()

            if not current_version:
                return {
                    "is_current": False,
                    "warning": "Document not found",
                    "requires_update": True,
                }

            # Check if document updated since last check
            if last_checked and current_version.discovered_at:
                if current_version.discovered_at > last_checked:
                    return {
                        "is_current": False,
                        "current_version": current_version.version_number,
                        "last_updated": current_version.discovered_at.isoformat(),
                        "requires_update": True,
                        "change_summary": current_version.change_summary,
                    }

            # Check staleness
            age_days = 0.0
            if current_version.discovered_at:
                age_days = (
                    datetime.utcnow() - current_version.discovered_at
                ).total_seconds() / 86400

            return {
                "is_current": True,
                "current_version": current_version.version_number,
                "age_days": int(age_days),
                "requires_update": False,
                "stale_warning": age_days > self.staleness_threshold_days,
            }

    async def verify_bulk_citations(
        self, citations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Verify multiple citations in bulk.

        Args:
            citations: List of citation dicts with file_id and excerpt

        Returns:
            Summary of verification results
        """
        results = []

        for citation in citations:
            file_id = citation.get("file_id", "")
            if not file_id:
                logger.warning(f"Skipping citation without file_id: {citation}")
                continue

            result = await self.verify_citation(
                file_id=file_id,
                excerpt=citation.get("excerpt"),
                metadata=citation,
            )
            results.append(result)

        # Calculate summary statistics
        total = len(results)
        current_count = sum(1 for r in results if r.is_current)
        superseded_count = sum(1 for r in results if r.is_superseded)
        with_warnings = sum(1 for r in results if r.warning)

        return {
            "total_citations": total,
            "current_citations": current_count,
            "superseded_citations": superseded_count,
            "citations_with_warnings": with_warnings,
            "verification_rate": current_count / total if total > 0 else 0,
            "results": results,
        }

    async def get_version_history(self, file_id: str) -> list[dict[str, Any]]:
        """Get version history for a document file.

        Args:
            file_id: Document file identifier

        Returns:
            List of version metadata dicts
        """
        with Session(engine) as session:
            statement = (
                select(DocumentVersion)
                .where(DocumentVersion.file_id == file_id)
                .order_by(desc(col(DocumentVersion.version_number)))
            )
            versions = session.exec(statement).all()

            return [
                {
                    "version_number": v.version_number,
                    "content_hash": v.content_hash,
                    "discovered_at": v.discovered_at.isoformat()
                    if v.discovered_at
                    else None,
                    "is_current": v.is_current,
                    "change_type": v.change_type,
                    "change_summary": v.change_summary,
                    "superseded_at": v.superseded_at.isoformat()
                    if v.superseded_at
                    else None,
                }
                for v in versions
            ]

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _extract_file_id(self, source: dict[str, Any]) -> str | None:
        """Extract file ID from source metadata.

        Args:
            source: Source document dict from chunk metadata

        Returns:
            File ID or None
        """
        # Try to get file_id directly (should be in chunk metadata)
        file_id = source.get("file_id")
        if file_id:
            return str(file_id)

        # Fallback: try spatial_metadata or other nested fields
        metadata = source.get("metadata", {})
        file_id = metadata.get("file_id")
        if file_id:
            return str(file_id)

        logger.warning(f"Could not find file_id in source metadata: {source.keys()}")
        return None

    async def _verify_quote(
        self,
        excerpt: str,
        version: DocumentVersion,
        session: Session,
    ) -> QuoteVerificationResult:
        """Verify that a quoted excerpt exists in the document version.

        Args:
            excerpt: Quoted text
            version: Document version to check against
            session: Database session

        Returns:
            QuoteVerificationResult with match information
        """
        from green_gov_rag.models.chunk import Chunk

        # Query chunks for this file_id
        statement = select(Chunk).where(Chunk.file_id == version.file_id)
        chunks = session.exec(statement).all()

        if not chunks:
            return QuoteVerificationResult(
                exact_match=False,
                similarity_score=0.0,
                found_in_version=None,
                warning="No chunks found for document",
            )

        # Normalize excerpt for comparison
        excerpt_normalized = excerpt.strip().lower()

        # Check for exact match in any chunk
        for chunk in chunks:
            chunk_text_normalized = chunk.text.lower()
            if excerpt_normalized in chunk_text_normalized:
                return QuoteVerificationResult(
                    exact_match=True,
                    similarity_score=1.0,
                    found_in_version=version.version_number,
                )

        # Fuzzy matching across all chunks to find best match
        best_similarity = 0.0
        best_chunk_text = ""

        for chunk in chunks:
            chunk_text_normalized = chunk.text.lower()
            similarity = difflib.SequenceMatcher(
                None, excerpt_normalized, chunk_text_normalized
            ).ratio()

            if similarity > best_similarity:
                best_similarity = similarity
                best_chunk_text = chunk.text[:100]  # Keep snippet for context

        # Determine match quality
        if best_similarity > 0.8:
            return QuoteVerificationResult(
                exact_match=False,
                similarity_score=best_similarity,
                found_in_version=version.version_number,
                snippet_context=best_chunk_text,
                warning="Close match found (not exact)",
            )
        elif best_similarity > 0.5:
            return QuoteVerificationResult(
                exact_match=False,
                similarity_score=best_similarity,
                found_in_version=None,
                snippet_context=best_chunk_text,
                warning="Partial match found, verify manually",
            )
        else:
            return QuoteVerificationResult(
                exact_match=False,
                similarity_score=best_similarity,
                found_in_version=None,
                warning="Quote not found in document chunks",
            )

    async def _verify_relevance(
        self,
        excerpt: str,
        query: str | None,
        answer: str,
        metadata: dict[str, Any] | None,
    ) -> float:
        """Verify if the excerpt is relevant to the answer using LLM.

        Args:
            excerpt: Quoted text from the document
            query: User's original query
            answer: Generated answer
            metadata: Source metadata for context

        Returns:
            Relevance score (0-1)
        """
        try:
            from green_gov_rag.rag.llm_factory import get_llm

            # Use configured LLM provider and model for relevance scoring
            # Use async invoke for parallel processing
            llm = get_llm(temperature=0, max_tokens=10)

            # Build context from metadata
            doc_title = (
                metadata.get("title", "Unknown document")
                if metadata
                else "Unknown document"
            )

            # Create prompt to evaluate relevance
            prompt = f"""You are evaluating whether a source excerpt supports an answer about Australian environmental/regulatory compliance.

QUERY: {query if query else "Not provided"}

ANSWER: {answer}

SOURCE EXCERPT:
{excerpt}

SOURCE DOCUMENT: {doc_title}

IMPORTANT: Evaluate METHODOLOGICAL relevance, not just industry/topic match.

Consider HIGHLY RELEVANT (0.8-1.0) if the source provides:
- Calculation formulas, measurement methods, or quantification approaches that apply to the query topic
- Regulatory frameworks (NGER, GHG Protocol, EPBC) that cover the query domain
- Standards, methodologies, or emission factors applicable across related industries
  Example: Coal mine fugitive emissions methods ARE directly applicable to gas pipeline fugitive emissions
  Example: NGER reporting requirements for one extractive industry apply to all extractive industries
- Legal/procedural requirements that transfer to the query context
- Federal legislation/standards as baseline for state/local queries (NCC for building, EPBC for environment)
- Planning scheme EIA requirements for environmental assessment queries (planning-environment overlap)

Consider SOMEWHAT RELEVANT (0.4-0.7) if:
- Same regulatory domain but different specific application (e.g., planning rules for different land types)
- General principles that require significant adaptation
- Framework documents that mention the topic tangentially
- Federal guidance when query is state-specific (provides context but not direct answer)
- Same-state but different Local Government Area (LGA) policies that may be transferable

Consider NOT RELEVANT (0.0-0.3) if:
- Completely different regulatory domain (building codes vs emissions, biodiversity vs construction)
- Different state/territory regulations addressing non-transferable local issues (NSW zoning vs VIC zoning)
- Different LGA-specific policies that are location-dependent (tree management in City A vs City B)
- Different country's regulations (unless explicitly about international standards)
- No methodological, legal, or procedural overlap

CRITICAL RULES:
1. If the source discusses calculation methods, emission factors, measurement approaches, or regulatory obligations in the same domain (e.g., any fugitive emissions from extractive industries), it IS highly relevant even if the specific industry differs.
2. For spatial queries (LGA/council-specific): Only sources for the SAME LGA or higher jurisdiction (state/federal) are highly relevant. Different LGA sources score ≤0.3 unless explicitly transferable.
3. For state-specific queries: Federal frameworks score 0.7-0.9 (baseline), same-state sources score 0.8-1.0, different-state sources score ≤0.3 unless methodologically identical.

Rate 0.0-1.0 (return ONLY the number):"""

            # Use ainvoke for async parallel execution
            response = await llm.ainvoke(prompt)
            score_text = response.content.strip()

            # Parse the score
            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            except ValueError:
                logger.warning(f"Could not parse relevance score: {score_text}")
                return 0.5  # Default to moderate relevance if parsing fails

        except Exception as e:
            logger.warning(f"Relevance verification failed: {e}")
            return 0.5  # Default to moderate relevance on error
