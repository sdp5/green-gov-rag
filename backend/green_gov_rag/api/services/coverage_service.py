"""LGA document coverage service."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from green_gov_rag.api.schemas import CoverageInfo


class CoverageService:
    """Service for LGA document coverage analysis."""

    # GitHub contribution URL template from env or default
    CONTRIBUTION_URL = (
        os.getenv("GITHUB_REPO_URL", "https://github.com/sdp5/green-gov-rag")
        + "/issues/new?template=add-document-source.md"
    )

    def __init__(self) -> None:
        """Initialize coverage service."""
        # Load documents config to analyze coverage
        self.documents_config = self._load_documents_config()

    def _load_documents_config(self) -> dict:
        """Load documents configuration from YAML.

        Returns:
            Parsed documents configuration
        """
        config_path = (
            Path(__file__).parent.parent.parent.parent
            / "configs"
            / "documents_config.yml"
        )

        if not config_path.exists():
            return {"documents": []}

        with open(config_path) as f:
            return yaml.safe_load(f) or {"documents": []}

    def get_lga_coverage(
        self,
        lga_code: Optional[str] = None,
        lga_name: Optional[str] = None,
    ) -> CoverageInfo:
        """Get document coverage information for a specific LGA.

        Args:
            lga_code: LGA code (e.g., "40070")
            lga_name: LGA name (e.g., "City of Adelaide")

        Returns:
            CoverageInfo with coverage details and contribution link
        """
        if not lga_code and not lga_name:
            # No LGA selected - return generic federal coverage
            return CoverageInfo(
                selected_lga=None,
                lga_code=None,
                has_local_coverage=False,
                local_doc_count=0,
                coverage_level="federal_only",
                contribution_url=self.CONTRIBUTION_URL,
            )

        # Count local documents for this LGA
        local_doc_count = self._count_local_documents(lga_code, lga_name)

        # Determine coverage level
        coverage_level = self._calculate_coverage_level(local_doc_count)

        return CoverageInfo(
            selected_lga=lga_name,
            lga_code=lga_code,
            has_local_coverage=local_doc_count > 0,
            local_doc_count=local_doc_count,
            coverage_level=coverage_level,
            contribution_url=self.CONTRIBUTION_URL,
        )

    def _count_local_documents(
        self,
        lga_code: Optional[str],
        lga_name: Optional[str],
    ) -> int:
        """Count local documents for a specific LGA.

        Args:
            lga_code: LGA code to search for
            lga_name: LGA name to search for

        Returns:
            Number of local documents found (counts download_urls if present)
        """
        documents = self.documents_config.get("documents", [])
        count = 0

        for doc in documents:
            # Only count local jurisdiction documents
            if doc.get("jurisdiction") != "local":
                continue

            # Check spatial metadata
            spatial_metadata = doc.get("spatial_metadata", {})
            matched = False

            # Match by LGA code
            if lga_code and lga_code in spatial_metadata.get("lga_codes", []):
                matched = True

            # Match by LGA name (case-insensitive partial match)
            if not matched and lga_name:
                doc_lga_names = spatial_metadata.get("lga_names", [])
                for doc_lga in doc_lga_names:
                    if (
                        lga_name.lower() in doc_lga.lower()
                        or doc_lga.lower() in lga_name.lower()
                    ):
                        matched = True
                        break

            # If matched, count download URLs or 1 document
            if matched:
                download_urls = doc.get("download_urls", [])
                count += len(download_urls) if download_urls else 1

        return count

    def _calculate_coverage_level(self, local_doc_count: int) -> str:
        """Calculate coverage level based on document count.

        Args:
            local_doc_count: Number of local documents

        Returns:
            Coverage level: "high", "medium", "low", or "none"
        """
        if local_doc_count == 0:
            return "none"
        elif local_doc_count >= 10:
            return "high"
        elif local_doc_count >= 5:
            return "medium"
        else:
            return "low"

    def get_all_covered_lgas(self) -> list[dict]:
        """Get list of all LGAs with document coverage.

        Returns:
            List of dicts with LGA info and document counts
        """
        documents = self.documents_config.get("documents", [])
        lga_coverage = {}

        for doc in documents:
            if doc.get("jurisdiction") != "local":
                continue

            spatial_metadata = doc.get("spatial_metadata", {})
            lga_codes = spatial_metadata.get("lga_codes", [])
            lga_names = spatial_metadata.get("lga_names", [])

            # Track coverage for each LGA code
            for i, lga_code in enumerate(lga_codes):
                lga_name = lga_names[i] if i < len(lga_names) else None

                if lga_code not in lga_coverage:
                    lga_coverage[lga_code] = {
                        "lga_code": lga_code,
                        "lga_name": lga_name,
                        "document_count": 0,
                    }

                lga_coverage[lga_code]["document_count"] += 1

        # Convert to list and add coverage levels
        result = []
        for lga_code, info in lga_coverage.items():
            coverage_level = self._calculate_coverage_level(info["document_count"])
            result.append(
                {
                    **info,
                    "coverage_level": coverage_level,
                    "has_local_coverage": info["document_count"] > 0,
                }
            )

        return sorted(result, key=lambda x: x["document_count"], reverse=True)
