"""Regulatory hierarchy and conflict detection service.

Handles:
1. Regulatory hierarchy (Federal > State > Local)
2. Cross-reference conflict detection
3. Jurisdiction precedence rules
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class JurisdictionLevel(str, Enum):
    """Regulatory jurisdiction levels in hierarchical order."""

    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"


# Jurisdiction hierarchy: higher number = higher precedence
JURISDICTION_PRECEDENCE = {
    JurisdictionLevel.FEDERAL: 3,
    JurisdictionLevel.STATE: 2,
    JurisdictionLevel.LOCAL: 1,
}


@dataclass
class RegulatoryDocument:
    """Representation of a regulatory document with hierarchy metadata."""

    document_id: str
    title: str
    jurisdiction: JurisdictionLevel
    region: str | None  # e.g., "NSW", "Queensland", "City of Adelaide"
    topic: str
    effective_date: str | None
    supersedes: list[str] | None = None  # List of document IDs this supersedes
    is_current: bool = True


@dataclass
class ConflictDetectionResult:
    """Result of cross-reference conflict detection."""

    has_conflict: bool
    conflict_type: str | None = None  # 'hierarchy', 'temporal', 'regional'
    conflicting_documents: list[dict[str, Any]] | None = None
    resolution: str | None = None  # How to resolve the conflict
    severity: str = "info"  # 'critical', 'warning', 'info'
    details: str | None = None


class RegulatoryHierarchyService:
    """Service for managing regulatory hierarchy and detecting conflicts.

    Handles:
    - Federal > State > Local precedence
    - Regional jurisdiction boundaries
    - Temporal precedence (newer supersedes older)
    - Cross-reference conflict detection
    """

    def __init__(self):
        """Initialize regulatory hierarchy service."""
        pass

    def get_jurisdiction_precedence(self, jurisdiction: str) -> int:
        """Get precedence level for a jurisdiction.

        Args:
            jurisdiction: Jurisdiction string ('federal', 'state', 'local')

        Returns:
            Precedence level (higher = more authoritative)
        """
        try:
            level = JurisdictionLevel(jurisdiction.lower())
            return JURISDICTION_PRECEDENCE[level]
        except (ValueError, KeyError):
            logger.warning(f"Unknown jurisdiction: {jurisdiction}, defaulting to 0")
            return 0

    def compare_documents(
        self, doc1: dict[str, Any], doc2: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare two documents to determine hierarchy.

        Args:
            doc1: First document metadata
            doc2: Second document metadata

        Returns:
            Comparison result with precedence information
        """
        j1 = doc1.get("jurisdiction", "").lower()
        j2 = doc2.get("jurisdiction", "").lower()

        p1 = self.get_jurisdiction_precedence(j1)
        p2 = self.get_jurisdiction_precedence(j2)

        if p1 > p2:
            return {
                "higher_authority": doc1,
                "lower_authority": doc2,
                "reason": f"{j1} takes precedence over {j2}",
            }
        elif p2 > p1:
            return {
                "higher_authority": doc2,
                "lower_authority": doc1,
                "reason": f"{j2} takes precedence over {j1}",
            }
        else:
            # Same level - check other factors
            return {
                "higher_authority": None,
                "lower_authority": None,
                "reason": "Same jurisdiction level - check temporal/regional precedence",
            }

    async def detect_conflicts(
        self, sources: list[dict[str, Any]], query_topic: str | None = None
    ) -> list[ConflictDetectionResult]:
        """Detect conflicts between multiple source documents.

        Args:
            sources: List of source documents
            query_topic: Optional topic to filter conflicts

        Returns:
            List of detected conflicts
        """
        conflicts: list[ConflictDetectionResult] = []

        # Group documents by topic
        topic_groups: dict[str, list[dict[str, Any]]] = {}
        for source in sources:
            topic = source.get("topic", "unknown")
            if topic not in topic_groups:
                topic_groups[topic] = []
            topic_groups[topic].append(source)

        # Check for conflicts within each topic
        for topic, docs in topic_groups.items():
            if len(docs) < 2:
                continue

            # Check for hierarchy conflicts
            hierarchy_conflicts = self._detect_hierarchy_conflicts(docs, topic)
            conflicts.extend(hierarchy_conflicts)

            # Check for regional conflicts
            regional_conflicts = self._detect_regional_conflicts(docs, topic)
            conflicts.extend(regional_conflicts)

        return conflicts

    def _detect_hierarchy_conflicts(
        self, documents: list[dict[str, Any]], topic: str
    ) -> list[ConflictDetectionResult]:
        """Detect hierarchy-based conflicts.

        E.g., Federal law vs State law on same topic.

        Args:
            documents: Documents to check
            topic: Topic being addressed

        Returns:
            List of hierarchy conflicts
        """
        conflicts: list[ConflictDetectionResult] = []

        # Sort by jurisdiction precedence
        sorted_docs = sorted(
            documents,
            key=lambda d: self.get_jurisdiction_precedence(d.get("jurisdiction", "")),
            reverse=True,
        )

        if len(sorted_docs) < 2:
            return conflicts

        # Check if lower jurisdictions contradict higher ones
        federal_docs = [
            d for d in sorted_docs if d.get("jurisdiction", "").lower() == "federal"
        ]
        state_docs = [
            d for d in sorted_docs if d.get("jurisdiction", "").lower() == "state"
        ]
        local_docs = [
            d for d in sorted_docs if d.get("jurisdiction", "").lower() == "local"
        ]

        # If we have federal + state/local on same topic, flag potential conflict
        if federal_docs and (state_docs or local_docs):
            conflicts.append(
                ConflictDetectionResult(
                    has_conflict=True,
                    conflict_type="hierarchy",
                    conflicting_documents=[
                        {
                            "title": federal_docs[0].get("title", "Unknown"),
                            "jurisdiction": "federal",
                        },
                        {
                            "title": (state_docs + local_docs)[0].get(
                                "title", "Unknown"
                            ),
                            "jurisdiction": (state_docs + local_docs)[0].get(
                                "jurisdiction"
                            ),
                        },
                    ],
                    resolution="Federal regulation takes precedence. Lower jurisdiction "
                    "documents may provide additional requirements but cannot contradict federal law.",
                    severity="warning",
                    details=f"Multiple jurisdiction levels found for topic: {topic}. "
                    "Verify that lower-level regulations comply with federal requirements.",
                )
            )

        return conflicts

    def _detect_regional_conflicts(
        self, documents: list[dict[str, Any]], topic: str
    ) -> list[ConflictDetectionResult]:
        """Detect regional jurisdiction conflicts.

        E.g., NSW vs VIC state laws, or overlapping LGA boundaries.

        Args:
            documents: Documents to check
            topic: Topic being addressed

        Returns:
            List of regional conflicts
        """
        conflicts = []

        # Group by jurisdiction level
        by_level: dict[str, list[dict[str, Any]]] = {}
        for doc in documents:
            level = doc.get("jurisdiction", "").lower()
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(doc)

        # Check for multiple regions at same level
        for level, docs in by_level.items():
            if len(docs) < 2:
                continue

            regions: set[str] = set()
            for doc in docs:
                region = doc.get("region")
                if region:
                    regions.add(str(region))

            if len(regions) > 1:
                conflicts.append(
                    ConflictDetectionResult(
                        has_conflict=True,
                        conflict_type="regional",
                        conflicting_documents=[
                            {
                                "title": d.get("title", "Unknown"),
                                "region": d.get("region"),
                                "jurisdiction": d.get("jurisdiction"),
                            }
                            for d in docs[:3]  # Limit to first 3
                        ],
                        resolution=f"Multiple regional regulations found at {level} level. "
                        f"Applicable regulation depends on geographic location.",
                        severity="info",
                        details=f"Regions: {', '.join(sorted(regions))}. "
                        f"Ensure correct regional jurisdiction applies to your case.",
                    )
                )

        return conflicts

    def calculate_source_authority_score(self, source: dict[str, Any]) -> float:
        """Calculate authority score for a source document.

        Higher score = more authoritative source.

        Args:
            source: Source document metadata

        Returns:
            Authority score (0-1)
        """
        score = 0.0

        # Jurisdiction precedence (0.4 weight)
        jurisdiction = source.get("jurisdiction", "").lower()
        precedence = self.get_jurisdiction_precedence(jurisdiction)
        max_precedence = max(JURISDICTION_PRECEDENCE.values())
        score += (precedence / max_precedence) * 0.4

        # Source type (0.2 weight)
        category = source.get("category", "").lower()
        category_weights = {
            "legislation": 1.0,
            "regulation": 0.9,
            "guideline": 0.7,
            "policy": 0.6,
        }
        score += category_weights.get(category, 0.5) * 0.2

        # Sovereignty (0.2 weight) - official government source
        is_sovereign = source.get("sovereign", True)
        score += (1.0 if is_sovereign else 0.5) * 0.2

        # Currency (0.2 weight) - is it the current version?
        is_current = source.get("is_current", True)
        score += (1.0 if is_current else 0.3) * 0.2

        return min(score, 1.0)

    def get_applicable_documents(
        self,
        sources: list[dict[str, Any]],
        user_region: str | None = None,
        user_jurisdiction: str | None = None,
    ) -> list[dict[str, Any]]:
        """Filter sources to only those applicable to user's jurisdiction.

        Args:
            sources: All source documents
            user_region: User's region (e.g., "NSW")
            user_jurisdiction: User's jurisdiction level

        Returns:
            Filtered list of applicable sources
        """
        applicable = []

        for source in sources:
            # Check jurisdiction match
            source_jurisdiction = source.get("jurisdiction", "").lower()

            # Federal always applies
            if source_jurisdiction == "federal":
                applicable.append(source)
                continue

            # State/Local only applies if region matches
            if user_region:
                source_region = source.get("region", "").lower()
                if user_region.lower() in source_region.lower():
                    applicable.append(source)
                    continue

        # Sort by authority (federal first, then state, then local)
        applicable.sort(
            key=lambda s: self.get_jurisdiction_precedence(s.get("jurisdiction", "")),
            reverse=True,
        )

        return applicable

    def generate_hierarchy_explanation(
        self, sources: list[dict[str, Any]]
    ) -> str | None:
        """Generate human-readable explanation of regulatory hierarchy.

        Args:
            sources: Source documents

        Returns:
            Explanation text or None
        """
        if len(sources) <= 1:
            return None

        jurisdictions = [s.get("jurisdiction", "").lower() for s in sources]
        unique_jurisdictions = set(jurisdictions)

        if len(unique_jurisdictions) == 1:
            return None

        explanation_parts = ["Multiple regulatory levels apply:"]

        if "federal" in unique_jurisdictions:
            federal_docs = [s for s in sources if s.get("jurisdiction") == "federal"]
            explanation_parts.append(
                f"• Federal level ({len(federal_docs)} document(s)) - "
                f"Takes precedence, applies nationwide"
            )

        if "state" in unique_jurisdictions:
            state_docs = [s for s in sources if s.get("jurisdiction") == "state"]
            regions: set[str] = {
                str(s.get("region")) for s in state_docs if s.get("region")
            }
            explanation_parts.append(
                f"• State level ({len(state_docs)} document(s)) - "
                f"Regions: {', '.join(sorted(regions))} - "
                f"Must comply with federal requirements"
            )

        if "local" in unique_jurisdictions:
            local_docs = [s for s in sources if s.get("jurisdiction") == "local"]
            explanation_parts.append(
                f"• Local level ({len(local_docs)} document(s)) - "
                f"Additional local requirements, must comply with federal and state"
            )

        return "\n".join(explanation_parts)
