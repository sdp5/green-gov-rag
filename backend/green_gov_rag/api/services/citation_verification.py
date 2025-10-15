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
        self, query_response: dict[str, Any]
    ) -> list[CitationVerificationResult]:
        """Verify all citations in a query response.

        Args:
            query_response: QueryResponse dict with sources

        Returns:
            List of verification results for each citation
        """
        results = []

        sources = query_response.get("sources", [])
        for source in sources:
            # Extract document identifier
            document_id = self._extract_document_id(source)
            if not document_id:
                logger.warning(f"Could not extract document_id from source: {source}")
                continue

            # Verify this citation
            result = await self.verify_citation(
                document_id=document_id,
                excerpt=source.get("excerpt"),
                metadata=source,
            )

            results.append(result)

        return results

    async def verify_citation(
        self,
        document_id: str,
        excerpt: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CitationVerificationResult:
        """Verify a single citation references the current document version.

        Args:
            document_id: Document identifier
            excerpt: Quoted text from the document
            metadata: Additional citation metadata

        Returns:
            CitationVerificationResult with verification status
        """
        with Session(engine) as session:
            # Get all versions of this document
            statement = (
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document_id)
                .order_by(desc(col(DocumentVersion.version_number)))
            )
            versions = session.exec(statement).all()

            if not versions:
                return CitationVerificationResult(
                    is_current=False,
                    confidence=0.0,
                    document_id=document_id,
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
                        document_id=document_id,
                        cited_version=cited_version_num,
                        current_version=current_version.version_number,
                        is_superseded=True,
                        superseded_at=cited_version_obj.superseded_at,
                        quote_match=quote_match,
                        quote_match_score=quote_match_score,
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
                document_id=document_id,
                cited_version=current_version.version_number,
                current_version=current_version.version_number,
                is_superseded=False,
                superseded_at=None,
                quote_match=quote_match,
                quote_match_score=quote_match_score,
                warning=warning,
            )

    async def check_citation_currency(
        self, document_id: str, last_checked: datetime | None = None
    ) -> dict[str, Any]:
        """Check if a citation is current or if document has been updated.

        Args:
            document_id: Document identifier
            last_checked: When the citation was last verified

        Returns:
            Dictionary with currency status and update information
        """
        with Session(engine) as session:
            # Get current version
            statement = (
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document_id)
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
            citations: List of citation dicts with document_id and excerpt

        Returns:
            Summary of verification results
        """
        results = []

        for citation in citations:
            result = await self.verify_citation(
                document_id=citation.get("document_id", ""),
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

    async def get_version_history(self, document_id: str) -> list[dict[str, Any]]:
        """Get version history for a document.

        Args:
            document_id: Document identifier

        Returns:
            List of version metadata dicts
        """
        with Session(engine) as session:
            statement = (
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document_id)
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

    def _extract_document_id(self, source: dict[str, Any]) -> str | None:
        """Extract document ID from source metadata.

        Args:
            source: Source document dict

        Returns:
            Document ID or None
        """
        # Try multiple ways to get document ID
        doc_id = source.get("document_id")
        if doc_id:
            return str(doc_id)

        # Generate from source URL
        source_url = source.get("source_url")
        if source_url:
            import hashlib

            # Use same ID generation as monitoring service
            url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
            return f"unknown_{url_hash}"

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
        # For now, this is a placeholder implementation
        # In a real system, you would:
        # 1. Load the document content from storage
        # 2. Search for the exact quote
        # 3. Use fuzzy matching if exact match not found

        # Placeholder: Check if we have metadata about the content
        metadata = version.metadata_ or {}
        document_content = metadata.get("content")

        if not document_content:
            return QuoteVerificationResult(
                exact_match=False,
                similarity_score=0.0,
                found_in_version=None,
                warning="Document content not available for verification",
            )

        # Check for exact match
        if excerpt in document_content:
            return QuoteVerificationResult(
                exact_match=True,
                similarity_score=1.0,
                found_in_version=version.version_number,
            )

        # Use fuzzy matching
        similarity = difflib.SequenceMatcher(
            None, excerpt.lower(), document_content.lower()
        ).ratio()

        return QuoteVerificationResult(
            exact_match=False,
            similarity_score=similarity,
            found_in_version=version.version_number if similarity > 0.8 else None,
            warning="Exact quote not found. Similarity-based match."
            if similarity > 0.8
            else "Quote not found in document",
        )
