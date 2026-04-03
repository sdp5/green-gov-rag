"""Federal legislation document sources.

This module implements document sources for Australian federal legislation
and regulations.
"""

from __future__ import annotations

from typing import Any

from green_gov_rag.etl.sources.base import (
    DocumentSource,
    MonitorableSource,
    ValidationResult,
)
from green_gov_rag.types import FEDERAL_VALID_CATEGORIES


class FederalLegislationSource(DocumentSource, MonitorableSource):
    """Document source for federal legislation and regulations.

    Handles federal-level documents such as:
    - EPBC Act (Environment Protection and Biodiversity Conservation)
    - National Construction Code (NCC)
    - Federal regulations and guidelines

    Example config:
        title: EPBC Act – Environment Protection and Biodiversity Conservation
        source_url: https://www.legislation.gov.au/Series/C2004A00485
        download_urls:
          - https://www.legislation.gov.au/C2004A00485/.../pdf/1
        jurisdiction: federal
        category: legislation
        topic: biodiversity
        region: Australia
        sovereign: true
    """

    def validate(self) -> ValidationResult:
        """Validate federal legislation configuration.

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        # Check required fields
        errors.extend(self._validate_required_fields())

        # Check URLs
        errors.extend(self._validate_urls())

        # Validate jurisdiction
        if self.config.get("jurisdiction") != "federal":
            errors.append(
                f"Invalid jurisdiction '{self.config.get('jurisdiction')}', "
                f"expected 'federal' for FederalLegislationSource"
            )

        # Validate category
        category = self.config.get("category", "")
        if category not in FEDERAL_VALID_CATEGORIES:
            warnings.append(
                f"Unusual category '{category}' for federal legislation. "
                f"Typical categories: {FEDERAL_VALID_CATEGORIES}"
            )

        # Check spatial metadata
        spatial = self.config.get("spatial_metadata", {})
        if spatial:
            if spatial.get("spatial_scope") != "federal":
                warnings.append(
                    f"Spatial scope '{spatial.get('spatial_scope')}' should be 'federal'"
                )
            if not spatial.get("applies_to_all_lgas", True):
                warnings.append("Federal documents typically apply to all LGAs")

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult(is_valid=True, errors=[], warnings=warnings)

    def get_download_urls(self) -> list[str]:
        """Get download URLs for federal legislation documents.

        Returns:
            List of URLs to download
        """
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata for federal legislation.

        Returns:
            Dictionary with title, jurisdiction, category, topic, etc.
        """
        metadata = {
            "title": self.config.get("title"),
            "jurisdiction": self.config.get("jurisdiction"),
            "category": self.config.get("category"),
            "topic": self.config.get("topic"),
            "region": self.config.get("region", "Australia"),
            "sovereign": self.config.get("sovereign", True),
            "source_url": self.config.get("source_url"),
        }

        # Include structured metadata (esg_metadata, spatial_metadata)
        metadata.update(self._extract_structured_metadata())

        return metadata

    def get_required_fields(self) -> list[str]:
        """Get required fields for federal legislation.

        Returns:
            List of required field names
        """
        return ["title", "jurisdiction", "category", "topic", "region"]

    def get_source_type(self) -> str:
        """Get source type identifier.

        Returns:
            'federal_legislation'
        """
        return "federal_legislation"

    def get_document_id(self, url: str) -> str:
        """Generate unique document ID for delta indexing.

        Uses default implementation from base class.

        Args:
            url: Download URL

        Returns:
            Document ID like "federal_legislation_epbc_act_2025"
        """
        return self._generate_document_id(url)

    def get_destination_path(self, url: str, base_dir: str = "data/raw") -> str:
        """Get filesystem path for downloaded document.

        Uses default implementation from base class.

        Args:
            url: Download URL
            base_dir: Base directory for raw documents

        Returns:
            Full path where file should be saved
        """
        return self._generate_destination_path(url, base_dir)
