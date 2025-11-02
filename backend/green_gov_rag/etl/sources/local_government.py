"""Local government document sources.

This module implements document sources for Local Government Area (LGA)
specific documents, policies, and development plans.
"""

from __future__ import annotations

from typing import Any

from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult


class LocalGovernmentSource(DocumentSource):
    """Document source for local government (LGA) documents.

    Handles LGA-specific documents such as:
    - Development plans and guidelines
    - Sustainability policies
    - Tree management strategies
    - Climate action plans
    - Local planning schemes

    Example config:
        title: City of Adelaide Development Guidelines
        source_url: https://www.cityofadelaide.com.au/planning
        download_urls:
          - https://d31atr86jnqrq2.cloudfront.net/.../guidelines.pdf
        jurisdiction: local
        category: development_plan
        topic: zoning
        region: City of Adelaide
        spatial_metadata:
          spatial_scope: local
          state: SA
          lga_codes: [40070]
          lga_names: [City of Adelaide]
          applies_to_all_lgas: false
    """

    def validate(self) -> ValidationResult:
        """Validate local government configuration.

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
        if self.config.get("jurisdiction") != "local":
            errors.append(
                f"Invalid jurisdiction '{self.config.get('jurisdiction')}', "
                f"expected 'local' for LocalGovernmentSource"
            )

        # Validate spatial metadata (critical for LGA documents)
        spatial = self.config.get("spatial_metadata", {})
        if not spatial:
            errors.append("Missing spatial_metadata for local government document")
        else:
            # Check spatial scope
            if spatial.get("spatial_scope") != "local":
                errors.append(
                    f"Spatial scope '{spatial.get('spatial_scope')}' should be 'local' "
                    f"for local government documents"
                )

            # Check LGA codes
            lga_codes = spatial.get("lga_codes", [])
            if not lga_codes:
                warnings.append(
                    "Missing lga_codes in spatial_metadata. "
                    "LGA-specific documents should specify applicable LGA codes"
                )

            # Check LGA names
            lga_names = spatial.get("lga_names", [])
            if not lga_names:
                warnings.append(
                    "Missing lga_names in spatial_metadata. "
                    "Consider adding LGA names for clarity"
                )

            # Validate applies_to_all_lgas is false
            if spatial.get("applies_to_all_lgas", False):
                warnings.append(
                    "applies_to_all_lgas should typically be 'false' for local documents"
                )

            # Check state is specified
            if not spatial.get("state"):
                warnings.append("Missing state in spatial_metadata for local document")

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult(is_valid=True, errors=[], warnings=warnings)

    def get_download_urls(self) -> list[str]:
        """Get download URLs for local government documents.

        Returns:
            List of URLs to download
        """
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata for local government document.

        Returns:
            Dictionary with title, jurisdiction, LGA info, etc.
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

        # Include spatial metadata (essential for LGA documents)
        if "spatial_metadata" in self.config:
            metadata["spatial_metadata"] = self.config["spatial_metadata"]

        # Include ESG metadata if present (for climate/sustainability plans)
        if "esg_metadata" in self.config:
            metadata["esg_metadata"] = self.config["esg_metadata"]

        return metadata

    def get_lga_codes(self) -> list[int]:
        """Get LGA codes for this document.

        Returns:
            List of LGA codes (e.g., [40070, 40280])
        """
        spatial = self.config.get("spatial_metadata", {})
        return spatial.get("lga_codes", [])

    def get_lga_names(self) -> list[str]:
        """Get LGA names for this document.

        Returns:
            List of LGA names (e.g., ['City of Adelaide'])
        """
        spatial = self.config.get("spatial_metadata", {})
        return spatial.get("lga_names", [])

    def get_state(self) -> str | None:
        """Get the state code for this LGA.

        Returns:
            State code (e.g., 'SA', 'NSW') or None
        """
        spatial = self.config.get("spatial_metadata", {})
        return spatial.get("state")

    def applies_to_point(self) -> bool:
        """Check if document applies to a specific point location.

        Returns:
            True if applies to point (e.g., airport), False otherwise
        """
        spatial = self.config.get("spatial_metadata", {})
        return spatial.get("applies_to_point", False)

    def get_required_fields(self) -> list[str]:
        """Get required fields for local government documents.

        Returns:
            List of required field names
        """
        return [
            "title",
            "jurisdiction",
            "category",
            "topic",
            "region",
            "spatial_metadata",
        ]

    def get_source_type(self) -> str:
        """Get source type identifier.

        Returns:
            'local_government'
        """
        return "local_government"

    def get_document_id(self, url: str) -> str:
        """Generate unique document ID for delta indexing.

        Uses default implementation from base class.

        Args:
            url: Download URL

        Returns:
            Document ID like "local_development_plan_zoning_city_of_adelaide"
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
