"""Emissions reporting document sources.

This module implements document sources for emissions reporting frameworks
including NGER, ISSB, GHG Protocol, and Scope 1/2/3 guidance.
"""

from __future__ import annotations

from typing import Any

from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult
from green_gov_rag.types import (
    VALID_EMISSION_SCOPES,
    VALID_ESG_FRAMEWORKS,
    VALID_GREENHOUSE_GASES,
)


class EmissionsReportingSource(DocumentSource):
    """Document source for emissions reporting and ESG frameworks.

    Handles documents related to:
    - NGER (National Greenhouse and Energy Reporting)
    - GHG Protocol (Scope 1, 2, 3)
    - ISSB Standards
    - Clean Energy Regulator guidelines
    - Safeguard Mechanism

    Example config:
        title: Clean Energy Regulator - Scope 1 Coal Mining Guideline
        source_url: https://cer.gov.au/
        download_urls:
          - https://cer.gov.au/document/estimating-emissions-...
        jurisdiction: federal
        category: environment
        topic: emissions_reporting
        esg_metadata:
          frameworks: [NGER, GHG_Protocol]
          emission_scopes: [scope_1]
          greenhouse_gases: [CO2, CH4, N2O]
          reportable_under_nger: true
    """

    def validate(self) -> ValidationResult:
        """Validate emissions reporting configuration.

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        # Check required fields
        errors.extend(self._validate_required_fields())

        # Check URLs
        errors.extend(self._validate_urls())

        # Validate ESG metadata presence
        esg_metadata = self.config.get("esg_metadata", {})
        if not esg_metadata:
            warnings.append(
                "Missing 'esg_metadata' field for emissions reporting document. "
                "Consider adding frameworks, emission_scopes, etc."
            )
        else:
            # Validate ESG metadata structure
            errors.extend(self._validate_esg_metadata(esg_metadata))

        # Check topic
        topic = self.config.get("topic", "")
        if topic not in ["emissions_reporting", "climate_change"]:
            warnings.append(
                f"Topic '{topic}' is unusual for emissions reporting. "
                f"Consider 'emissions_reporting' or 'climate_change'"
            )

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult(is_valid=True, errors=[], warnings=warnings)

    def get_download_urls(self) -> list[str]:
        """Get download URLs for emissions reporting documents.

        Returns:
            List of URLs to download
        """
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata for emissions reporting document.

        Returns:
            Dictionary with title, jurisdiction, ESG metadata, etc.
        """
        metadata = {
            "title": self.config.get("title"),
            "jurisdiction": self.config.get("jurisdiction"),
            "category": self.config.get("category"),
            "topic": self.config.get("topic"),
            "region": self.config.get("region"),
            "sovereign": self.config.get("sovereign", True),
            "source_url": self.config.get("source_url"),
        }

        # Include ESG metadata
        if "esg_metadata" in self.config:
            metadata["esg_metadata"] = self.config["esg_metadata"]

        # Include spatial metadata
        if "spatial_metadata" in self.config:
            metadata["spatial_metadata"] = self.config["spatial_metadata"]

        return metadata

    def get_esg_metadata(self) -> dict[str, Any]:
        """Get ESG-specific metadata.

        Returns:
            ESG metadata dictionary
        """
        return self.config.get("esg_metadata", {})

    def get_emission_scopes(self) -> list[str]:
        """Get emission scopes covered by this document.

        Returns:
            List of scopes (e.g., ['scope_1', 'scope_2'])
        """
        esg = self.get_esg_metadata()
        return esg.get("emission_scopes", [])

    def get_scope_3_categories(self) -> list[str]:
        """Get Scope 3 categories covered by this document.

        Returns:
            List of Scope 3 categories (e.g., ['purchased_goods_services'])
        """
        esg = self.get_esg_metadata()
        return esg.get("scope_3_categories", [])

    def is_nger_reportable(self) -> bool:
        """Check if document is reportable under NGER.

        Returns:
            True if reportable under NGER, False otherwise
        """
        esg = self.get_esg_metadata()
        return esg.get("reportable_under_nger", False)

    def get_source_type(self) -> str:
        """Get source type identifier.

        Returns:
            'emissions_reporting'
        """
        return "emissions_reporting"

    def get_document_id(self, url: str) -> str:
        """Generate unique document ID for delta indexing.

        Uses default implementation from base class.

        Args:
            url: Download URL

        Returns:
            Document ID like "federal_environment_emissions_reporting_nger_guideline"
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

    def _validate_esg_metadata(self, esg_metadata: dict[str, Any]) -> list[str]:
        """Validate ESG metadata structure.

        Args:
            esg_metadata: ESG metadata dictionary

        Returns:
            List of validation errors
        """
        errors = []

        # Check emission scopes
        emission_scopes = esg_metadata.get("emission_scopes", [])
        for scope in emission_scopes:
            if scope not in VALID_EMISSION_SCOPES:
                errors.append(
                    f"Invalid emission scope: {scope}. Valid: {VALID_EMISSION_SCOPES}"
                )

        # Check Scope 3 categories (if applicable)
        if "scope_3" in emission_scopes:
            scope_3_cats = esg_metadata.get("scope_3_categories", [])
            if not scope_3_cats:
                errors.append("Scope 3 documents must specify scope_3_categories")

        # Check greenhouse gases
        ghg_gases = esg_metadata.get("greenhouse_gases", [])
        for gas in ghg_gases:
            if gas not in VALID_GREENHOUSE_GASES:
                errors.append(
                    f"Invalid greenhouse gas: {gas}. Valid: {VALID_GREENHOUSE_GASES}"
                )

        # Check frameworks
        frameworks = esg_metadata.get("frameworks", [])
        for framework in frameworks:
            if framework not in VALID_ESG_FRAMEWORKS:
                # Warning only, as new frameworks may be added
                pass

        return errors
