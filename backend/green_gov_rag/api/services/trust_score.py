"""Trust score calculation for RAG responses.

Calculates a composite trust score based on:
1. Citation verification (are sources current and accurate?)
2. Source authority (jurisdiction hierarchy, sovereignty)
3. Conflict detection (are sources contradictory?)
4. Quote accuracy (does cited text match source?)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TrustScoreBreakdown:
    """Detailed breakdown of trust score components."""

    overall_score: float  # 0-1, composite trust score
    citation_score: float  # 0-1, citation verification quality
    authority_score: float  # 0-1, source authority level
    conflict_score: float  # 0-1, lack of conflicts (1.0 = no conflicts)
    accuracy_score: float  # 0-1, quote/content accuracy
    confidence_level: str  # "high", "medium", "low"
    warnings: list[str]  # List of trust warnings
    details: dict[str, Any]  # Additional scoring details


class TrustScoreService:
    """Service for calculating trust scores for RAG responses.

    Trust score is a composite metric (0-1) indicating how much confidence
    users should have in the RAG response based on:
    - Citation quality and currency
    - Source authority and jurisdiction
    - Presence of conflicts
    - Quote accuracy
    """

    # Weight configuration for score components
    WEIGHTS = {
        "citation": 0.35,  # Is source current and properly cited?
        "authority": 0.30,  # How authoritative is the source?
        "conflict": 0.20,  # Are there conflicting sources?
        "accuracy": 0.15,  # Does quoted text match source?
    }

    # Thresholds for confidence levels
    HIGH_CONFIDENCE_THRESHOLD = 0.80
    MEDIUM_CONFIDENCE_THRESHOLD = 0.60

    def __init__(self):
        """Initialize trust score service."""
        pass

    def calculate_trust_score(
        self,
        citation_results: list[Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
        conflicts: list[Any] | None = None,
        authority_scores: dict[str, float] | None = None,
    ) -> TrustScoreBreakdown:
        """Calculate composite trust score for a RAG response.

        Args:
            citation_results: List of CitationVerificationResult objects
            sources: List of source documents
            conflicts: List of ConflictDetectionResult objects
            authority_scores: Pre-calculated authority scores per source

        Returns:
            TrustScoreBreakdown with detailed scoring
        """
        warnings: list[str] = []

        # Calculate individual component scores
        citation_score = self._calculate_citation_score(citation_results, warnings)
        authority_score = self._calculate_authority_score(
            sources, authority_scores, warnings
        )
        conflict_score = self._calculate_conflict_score(conflicts, warnings)
        accuracy_score = self._calculate_accuracy_score(citation_results, warnings)

        # Calculate weighted composite score
        overall_score = (
            citation_score * self.WEIGHTS["citation"]
            + authority_score * self.WEIGHTS["authority"]
            + conflict_score * self.WEIGHTS["conflict"]
            + accuracy_score * self.WEIGHTS["accuracy"]
        )

        # Determine confidence level
        if overall_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence_level = "high"
        elif overall_score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence_level = "medium"
        else:
            confidence_level = "low"
            warnings.append("Low trust score - verify answer against original sources")

        return TrustScoreBreakdown(
            overall_score=overall_score,
            citation_score=citation_score,
            authority_score=authority_score,
            conflict_score=conflict_score,
            accuracy_score=accuracy_score,
            confidence_level=confidence_level,
            warnings=warnings,
            details={
                "weights": self.WEIGHTS,
                "num_sources": len(sources) if sources else 0,
                "num_conflicts": len(conflicts) if conflicts else 0,
                "num_citations": len(citation_results) if citation_results else 0,
            },
        )

    def _calculate_citation_score(
        self, citation_results: list[Any] | None, warnings: list[str]
    ) -> float:
        """Calculate citation quality score.

        Args:
            citation_results: Citation verification results
            warnings: List to append warnings to

        Returns:
            Citation score (0-1)
        """
        if not citation_results:
            warnings.append("No citation verification performed")
            return 0.0  # No verification = no confidence

        total_score = 0.0
        superseded_count = 0
        stale_count = 0

        for result in citation_results:
            # Start with base score
            score = 1.0

            # Penalize if not current
            if not result.is_current:
                score *= 0.5
                superseded_count += 1

            # Penalize if superseded
            if result.is_superseded:
                score *= 0.3
                warnings.append(
                    f"Citing superseded document: {result.document_id} "
                    f"(v{result.cited_version} → v{result.current_version})"
                )

            # Small penalty for warnings (staleness, etc.)
            if result.warning:
                score *= 0.9
                stale_count += 1

            # Use confidence from verification
            score *= result.confidence

            total_score += score

        avg_score = total_score / len(citation_results)

        if superseded_count > 0:
            warnings.append(
                f"{superseded_count}/{len(citation_results)} citations are superseded"
            )

        if stale_count > len(citation_results) / 2:
            warnings.append("More than half of citations may be stale")

        return avg_score

    def _calculate_authority_score(
        self,
        sources: list[dict[str, Any]] | None,
        authority_scores: dict[str, float] | None,
        warnings: list[str],
    ) -> float:
        """Calculate source authority score.

        Args:
            sources: Source documents
            authority_scores: Pre-calculated scores
            warnings: List to append warnings to

        Returns:
            Authority score (0-1)
        """
        if not sources:
            warnings.append("No sources provided")
            return 0.0

        if authority_scores:
            # Use pre-calculated scores
            return sum(authority_scores.values()) / len(authority_scores)

        # Calculate based on jurisdiction and category
        total_score = 0.0
        non_sovereign_count = 0

        for source in sources:
            score = 0.5  # Base score

            # Jurisdiction bonus
            jurisdiction = source.get("jurisdiction", "").lower()
            if jurisdiction == "federal":
                score += 0.3
            elif jurisdiction == "state":
                score += 0.2
            elif jurisdiction == "local":
                score += 0.1

            # Category bonus
            category = source.get("category", "").lower()
            if category == "legislation":
                score += 0.2
            elif category == "regulation":
                score += 0.15
            elif category == "guideline":
                score += 0.1

            # Sovereignty check
            if not source.get("sovereign", True):
                score *= 0.7
                non_sovereign_count += 1

            total_score += min(score, 1.0)

        if non_sovereign_count > 0:
            warnings.append(
                f"{non_sovereign_count}/{len(sources)} sources are not official government documents"
            )

        return total_score / len(sources)

    def _calculate_conflict_score(
        self, conflicts: list[Any] | None, warnings: list[str]
    ) -> float:
        """Calculate conflict score (1.0 = no conflicts).

        Args:
            conflicts: List of ConflictDetectionResult
            warnings: List to append warnings to

        Returns:
            Conflict score (0-1, higher = fewer conflicts)
        """
        if not conflicts:
            return 1.0  # No conflicts = perfect score

        # Count conflicts by severity
        critical_count = sum(1 for c in conflicts if c.severity == "critical")
        warning_count = sum(1 for c in conflicts if c.severity == "warning")
        info_count = sum(1 for c in conflicts if c.severity == "info")

        # Calculate penalty
        penalty = (critical_count * 0.4) + (warning_count * 0.2) + (info_count * 0.1)

        score = max(0.0, 1.0 - penalty)

        # Add warnings
        if critical_count > 0:
            warnings.append(
                f"{critical_count} critical conflict(s) detected - verify regulatory precedence"
            )

        if warning_count > 0:
            warnings.append(f"{warning_count} potential conflict(s) between sources")

        return score

    def _calculate_accuracy_score(
        self, citation_results: list[Any] | None, warnings: list[str]
    ) -> float:
        """Calculate quote/content accuracy score.

        Args:
            citation_results: Citation verification results
            warnings: List to append warnings to

        Returns:
            Accuracy score (0-1)
        """
        if not citation_results:
            return 0.5  # LLM baseline accuracy, but unverified

        verified_count = 0
        total_with_quotes = 0
        mismatch_count = 0

        for result in citation_results:
            if result.quote_match is not None:
                total_with_quotes += 1

                if result.quote_match:
                    verified_count += 1
                else:
                    mismatch_count += 1

        if total_with_quotes == 0:
            # No quotes to verify
            return 0.7  # Assume reasonable accuracy

        accuracy = verified_count / total_with_quotes

        # Cap at 0.95 to acknowledge inherent uncertainty (OCR errors, version differences, etc.)
        accuracy = min(accuracy, 0.95)

        if mismatch_count > 0:
            warnings.append(
                f"{mismatch_count}/{total_with_quotes} quoted excerpts don't match source exactly"
            )

        return accuracy

    def get_trust_level_description(self, score: float) -> str:
        """Get human-readable description of trust level.

        Args:
            score: Trust score (0-1)

        Returns:
            Description string
        """
        if score >= 0.90:
            return "Excellent - Highly reliable, current sources with no conflicts"
        elif score >= 0.80:
            return "High - Reliable sources, minor warnings only"
        elif score >= 0.70:
            return "Good - Generally reliable, verify important details"
        elif score >= 0.60:
            return "Medium - Some concerns, cross-check critical information"
        elif score >= 0.50:
            return "Fair - Multiple concerns, independent verification recommended"
        else:
            return "Low - Significant concerns, do not rely without verification"

    def format_trust_score_display(self, breakdown: TrustScoreBreakdown) -> str:
        """Format trust score for display to users.

        Args:
            breakdown: Trust score breakdown

        Returns:
            Formatted string for display
        """
        lines = [
            f"Trust Score: {breakdown.overall_score:.1%} ({breakdown.confidence_level})",
            f"  • Citation Quality: {breakdown.citation_score:.1%}",
            f"  • Source Authority: {breakdown.authority_score:.1%}",
            f"  • Conflict Check: {breakdown.conflict_score:.1%}",
            f"  • Quote Accuracy: {breakdown.accuracy_score:.1%}",
        ]

        if breakdown.warnings:
            lines.append("\nWarnings:")
            for warning in breakdown.warnings:
                lines.append(f"  ⚠ {warning}")

        return "\n".join(lines)
