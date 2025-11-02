"""Factory for creating document sources.

This module provides a factory pattern for instantiating the appropriate
document source type based on configuration.
"""

from __future__ import annotations

import logging
from typing import Any

from green_gov_rag.etl.sources.base import DocumentSource
from green_gov_rag.etl.sources.emissions import EmissionsReportingSource
from green_gov_rag.etl.sources.federal import FederalLegislationSource
from green_gov_rag.etl.sources.local_government import LocalGovernmentSource
from green_gov_rag.etl.sources.registry import DocumentSourceRegistry
from green_gov_rag.etl.sources.state import StateLegislationSource

logger = logging.getLogger(__name__)


class DocumentSourceFactory:
    """Factory for creating document sources from configuration.

    The factory automatically infers the appropriate source type from
    document configuration and instantiates the correct class.

    Example:
        >>> factory = DocumentSourceFactory()
        >>> config = {"jurisdiction": "federal", "category": "legislation", ...}
        >>> source = factory.create_source(config)
        >>> isinstance(source, FederalLegislationSource)
        True
    """

    def __init__(self, registry: DocumentSourceRegistry | None = None):
        """Initialize factory with optional custom registry.

        Args:
            registry: Custom registry to use. If None, creates default registry.
        """
        self.registry = registry or self._create_default_registry()

    def _create_default_registry(self) -> DocumentSourceRegistry:
        """Create and populate default registry with built-in sources.

        Returns:
            Configured registry with all built-in source types
        """
        registry = DocumentSourceRegistry()

        # Register built-in source types
        registry.register("federal_legislation", FederalLegislationSource)
        registry.register("emissions_reporting", EmissionsReportingSource)
        registry.register("state_legislation", StateLegislationSource)
        registry.register("local_government", LocalGovernmentSource)

        # Register generic fallback
        registry.register("generic", GenericDocumentSource)

        return registry

    def create_source(self, config: dict[str, Any]) -> DocumentSource:
        """Create appropriate document source from configuration.

        Args:
            config: Document configuration dictionary

        Returns:
            Instantiated DocumentSource subclass

        Raises:
            ValueError: If configuration is invalid or source type not found
        """
        # Infer source type
        source_type = self._infer_source_type(config)

        # Get source class from registry
        source_class = self.registry.get(source_type)
        if not source_class:
            logger.warning(
                f"No registered source for type '{source_type}', using generic"
            )
            source_class = self.registry.get("generic")

        if source_class is None:
            msg = f"No source class found for type '{source_type}' and no generic fallback"
            raise ValueError(msg)

        # Instantiate and return
        try:
            return source_class(config)
        except Exception as e:
            logger.error(
                f"Failed to create source for {config.get('title', 'unknown')}: {e}"
            )
            raise

    def create_sources_from_list(
        self, configs: list[dict[str, Any]]
    ) -> list[DocumentSource]:
        """Create multiple document sources from list of configurations.

        Args:
            configs: List of document configuration dictionaries

        Returns:
            List of instantiated DocumentSource objects
        """
        sources = []
        for config in configs:
            try:
                source = self.create_source(config)
                sources.append(source)
            except Exception as e:
                logger.error(f"Skipping document due to error: {e}")
                continue
        return sources

    def _infer_source_type(self, config: dict[str, Any]) -> str:
        """Infer source type from document configuration.

        Args:
            config: Document configuration dictionary

        Returns:
            Inferred source type identifier
        """
        jurisdiction = config.get("jurisdiction", "").lower()
        category = config.get("category", "").lower()
        topic = config.get("topic", "").lower()

        # Check for emissions reporting
        if "esg_metadata" in config or topic in [
            "emissions_reporting",
            "climate_change",
        ]:
            # Special case: state/local climate acts might have esg_metadata
            # but are better handled by state/local sources
            if jurisdiction in ["state", "local"] and category in [
                "legislation",
                "policy",
            ]:
                if jurisdiction == "local":
                    return "local_government"
                return "state_legislation"
            return "emissions_reporting"

        # Check for local government
        if jurisdiction == "local":
            return "local_government"

        # Check for state legislation
        if jurisdiction == "state":
            return "state_legislation"

        # Check for federal legislation
        if jurisdiction == "federal":
            if category in ["legislation", "regulation", "building", "policy"]:
                return "federal_legislation"

        # Default fallback
        return "generic"


class GenericDocumentSource(DocumentSource):
    """Generic fallback document source for unrecognized types.

    This source provides basic functionality for documents that don't
    fit into specific categories.
    """

    def validate(self) -> Any:
        """Validate generic document configuration.

        Returns:
            ValidationResult with basic validation
        """
        from green_gov_rag.etl.sources.base import ValidationResult

        errors = self._validate_required_fields()
        errors.extend(self._validate_urls())

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def get_download_urls(self) -> list[str]:
        """Get download URLs.

        Returns:
            List of URLs
        """
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata.

        Returns:
            Full configuration as metadata
        """
        return dict(self.config)

    def get_source_type(self) -> str:
        """Get source type identifier.

        Returns:
            'generic'
        """
        return "generic"

    def get_document_id(self, url: str) -> str:
        """Generate document ID using default implementation.

        Args:
            url: Download URL

        Returns:
            Document ID
        """
        return self._generate_document_id(url)

    def get_destination_path(self, url: str, base_dir: str = "data/raw") -> str:
        """Generate destination path using default implementation.

        Args:
            url: Download URL
            base_dir: Base directory

        Returns:
            Destination path
        """
        return self._generate_destination_path(url, base_dir)
