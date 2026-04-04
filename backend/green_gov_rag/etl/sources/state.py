"""State legislation document sources.

This module implements document sources for Australian state-level legislation,
regulations, and policies.
"""

from __future__ import annotations

from typing import Any

from green_gov_rag.etl.sources.base import (
    DocumentSource,
    MonitorableSource,
    ValidationResult,
)
from green_gov_rag.types import STATE_CODE_TO_NAME, AustralianState


class StateLegislationSource(DocumentSource, MonitorableSource):
    """Document source for state-level legislation and regulations.

    Handles state-level documents from:
    - New South Wales (NSW)
    - Victoria (VIC)
    - Queensland (QLD)
    - South Australia (SA)
    - Western Australia (WA)
    - Tasmania (TAS)
    - Northern Territory (NT)
    - Australian Capital Territory (ACT)

    Example config:
        title: NSW Environmental Planning and Assessment Act 1979
        source_url: https://legislation.nsw.gov.au/...
        download_urls:
          - https://legislation.nsw.gov.au/.../pdf
        jurisdiction: state
        category: legislation
        topic: environmental_planning
        region: New South Wales
        spatial_metadata:
          spatial_scope: state
          state: NSW
          applies_to_all_lgas: true
    """

    VALID_STATES = [state.value for state in AustralianState]

    def validate(self) -> ValidationResult:
        """Validate state legislation configuration.

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
        if self.config.get("jurisdiction") != "state":
            errors.append(
                f"Invalid jurisdiction '{self.config.get('jurisdiction')}', "
                f"expected 'state' for StateLegislationSource"
            )

        # Validate state in spatial metadata
        spatial = self.config.get("spatial_metadata", {})
        if spatial:
            state = spatial.get("state")
            if state not in self.VALID_STATES:
                errors.append(
                    f"Invalid state '{state}' in spatial_metadata. "
                    f"Valid states: {self.VALID_STATES}"
                )

            if spatial.get("spatial_scope") != "state":
                warnings.append(
                    f"Spatial scope '{spatial.get('spatial_scope')}' should be 'state' "
                    f"for state legislation"
                )

            if not spatial.get("applies_to_all_lgas", True):
                warnings.append(
                    "State legislation typically applies to all LGAs within the state"
                )
        else:
            warnings.append("Missing spatial_metadata for state legislation")

        # Validate region matches state
        region = self.config.get("region", "")
        if spatial and spatial.get("state"):
            state_code = spatial["state"]
            expected_region = STATE_CODE_TO_NAME.get(state_code)
            if expected_region and region != expected_region:
                warnings.append(
                    f"Region '{region}' doesn't match state '{state_code}'. "
                    f"Expected '{expected_region}'"
                )

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult(is_valid=True, errors=[], warnings=warnings)

    def get_download_urls(self) -> list[str]:
        """Get download URLs for state legislation documents.

        Returns:
            List of URLs to download
        """
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata for state legislation.

        Returns:
            Dictionary with title, jurisdiction, state, etc.
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

        # Include spatial metadata
        if "spatial_metadata" in self.config:
            metadata["spatial_metadata"] = self.config["spatial_metadata"]

        # Include ESG metadata if present (for climate change acts, etc.)
        if "esg_metadata" in self.config:
            metadata["esg_metadata"] = self.config["esg_metadata"]

        return metadata

    def get_state(self) -> str | None:
        """Get the state code for this legislation.

        Returns:
            State code (e.g., 'NSW', 'VIC') or None
        """
        spatial = self.config.get("spatial_metadata", {})
        return spatial.get("state")

    def get_required_fields(self) -> list[str]:
        """Get required fields for state legislation.

        Returns:
            List of required field names
        """
        return ["title", "jurisdiction", "category", "topic", "region"]

    def get_source_type(self) -> str:
        """Get source type identifier.

        Returns:
            'state_legislation'
        """
        return "state_legislation"

    def get_document_id(self, url: str) -> str:
        """Generate unique document ID for delta indexing.

        Uses default implementation from base class.

        Args:
            url: Download URL

        Returns:
            Document ID like "state_legislation_environmental_planning_nsw_epa_act"
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
