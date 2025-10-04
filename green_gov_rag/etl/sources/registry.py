"""Registry for document source plugins.

This module provides a registry pattern for auto-discovering and managing
document source plugins, enabling easy extension by contributors.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Type

import yaml

from green_gov_rag.etl.sources.base import DocumentSource

logger = logging.getLogger(__name__)


class DocumentSourceRegistry:
    """Registry for managing document source plugins.

    This registry enables plugin-based architecture where new document
    source types can be registered and auto-discovered.

    Example:
        >>> registry = DocumentSourceRegistry()
        >>> registry.register("federal_legislation", FederalLegislationSource)
        >>> sources = registry.load_from_config("configs/documents_config.yml")
    """

    def __init__(self):
        """Initialize empty registry."""
        self._sources: dict[str, Type[DocumentSource]] = {}

    def register(self, source_type: str, source_class: Type[DocumentSource]) -> None:
        """Register a document source plugin.

        Args:
            source_type: Identifier for this source type (e.g., 'federal_legislation')
            source_class: Class implementing DocumentSource interface

        Raises:
            ValueError: If source_class doesn't inherit from DocumentSource
        """
        # Validate source class inherits from DocumentSource
        # Note: mypy incorrectly flags the code after this as unreachable
        # This is a known limitation with Type[T] parameters and issubclass()
        if not issubclass(source_class, DocumentSource):
            msg = f"{source_class.__name__} must inherit from DocumentSource"  # type: ignore[unreachable]
            raise ValueError(msg)

        # Check and warn if overwriting existing registration
        if source_type in self._sources:
            logger.warning(f"Overwriting existing source type: {source_type}")

        # Register the source
        self._sources[source_type] = source_class
        logger.debug(
            f"Registered source type: {source_type} -> {source_class.__name__}"
        )

    def get(self, source_type: str) -> Type[DocumentSource] | None:
        """Get a registered source class by type.

        Args:
            source_type: Identifier for the source type

        Returns:
            Source class if registered, None otherwise
        """
        return self._sources.get(source_type)

    def get_all_types(self) -> list[str]:
        """Get list of all registered source types.

        Returns:
            List of registered source type identifiers
        """
        return list(self._sources.keys())

    def is_registered(self, source_type: str) -> bool:
        """Check if a source type is registered.

        Args:
            source_type: Identifier to check

        Returns:
            True if registered, False otherwise
        """
        return source_type in self._sources

    def load_from_config(
        self,
        config_path: str | Path,
        source_type: str | None = None,
    ) -> list[DocumentSource]:
        """Load document sources from YAML configuration.

        Args:
            config_path: Path to documents_config.yml
            source_type: Optional filter for specific source type

        Returns:
            List of instantiated DocumentSource objects

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config_file = Path(config_path)
        if not config_file.exists():
            msg = f"Config file {config_path} not found"
            raise FileNotFoundError(msg)

        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        documents = config.get("documents", [])
        sources = []

        for doc_config in documents:
            # Infer source type from document config
            inferred_type = self._infer_source_type(doc_config)

            # Skip if filtering by type and doesn't match
            if source_type and inferred_type != source_type:
                continue

            # Get registered source class
            source_class = self._sources.get(inferred_type)
            if not source_class:
                logger.warning(
                    f"No registered source for type '{inferred_type}' "
                    f"(document: {doc_config.get('title', 'unknown')})"
                )
                continue

            # Instantiate source
            try:
                source = source_class(doc_config)
                sources.append(source)
            except Exception as e:
                logger.error(
                    f"Failed to create source for {doc_config.get('title', 'unknown')}: {e}"
                )

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
            return "emissions_reporting"

        # Check for local government
        if jurisdiction == "local":
            return "local_government"

        # Check for state legislation
        if jurisdiction == "state":
            return "state_legislation"

        # Check for federal legislation
        if jurisdiction == "federal":
            if category in ["legislation", "regulation"]:
                return "federal_legislation"

        # Default fallback
        return "generic"

    def auto_discover_plugins(
        self, plugins_package: str = "green_gov_rag.etl.sources"
    ) -> None:
        """Auto-discover and register plugins from a package.

        Args:
            plugins_package: Python package to scan for plugins
        """
        # This is a placeholder for future plugin auto-discovery
        # Implementation would use importlib to scan for DocumentSource subclasses
        logger.info(f"Auto-discovery from {plugins_package} not yet implemented")


# Global registry instance
_global_registry = DocumentSourceRegistry()


def get_global_registry() -> DocumentSourceRegistry:
    """Get the global document source registry.

    Returns:
        Global registry instance
    """
    return _global_registry
