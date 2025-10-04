"""Base interface for document sources.

This module defines the core abstraction for document sources,
enabling a plugin-based architecture for adding new document types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """Result of document source validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]

    @classmethod
    def success(cls) -> ValidationResult:
        """Create a successful validation result."""
        return cls(is_valid=True, errors=[], warnings=[])

    @classmethod
    def failure(
        cls, errors: list[str], warnings: list[str] | None = None
    ) -> ValidationResult:
        """Create a failed validation result."""
        return cls(is_valid=False, errors=errors, warnings=warnings or [])


class DocumentSource(ABC):
    """Base interface for document sources.

    Each document source type (federal legislation, emissions reporting, etc.)
    should implement this interface to enable standardized processing.

    Example:
        >>> class MySource(DocumentSource):
        ...     def __init__(self, config: dict):
        ...         self.config = config
        ...
        ...     def validate(self) -> ValidationResult:
        ...         # Validation logic
        ...         return ValidationResult.success()
        ...
        ...     def get_download_urls(self) -> list[str]:
        ...         return self.config.get("download_urls", [])
        ...
        ...     def get_metadata(self) -> dict:
        ...         return {"title": self.config["title"]}
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize document source with configuration.

        Args:
            config: Document configuration dictionary from YAML
        """
        self.config = config

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Validate the document source configuration.

        Returns:
            ValidationResult indicating success/failure with errors/warnings
        """
        pass

    @abstractmethod
    def get_download_urls(self) -> list[str]:
        """Get list of URLs to download for this document.

        Returns:
            List of download URLs
        """
        pass

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """Get metadata for this document.

        Returns:
            Dictionary containing document metadata (title, jurisdiction, etc.)
        """
        pass

    def get_source_type(self) -> str:
        """Get the type identifier for this source.

        Returns:
            String identifier (e.g., 'federal_legislation', 'emissions_reporting')
        """
        return self.__class__.__name__.replace("Source", "").lower()

    def get_required_fields(self) -> list[str]:
        """Get list of required configuration fields.

        Returns:
            List of required field names
        """
        return ["title", "jurisdiction", "category", "topic"]

    def get_optional_fields(self) -> list[str]:
        """Get list of optional configuration fields.

        Returns:
            List of optional field names
        """
        return [
            "source_url",
            "download_urls",
            "region",
            "sovereign",
            "esg_metadata",
            "spatial_metadata",
        ]

    def _validate_required_fields(self) -> list[str]:
        """Check that all required fields are present.

        Returns:
            List of error messages for missing fields
        """
        errors = []
        for field in self.get_required_fields():
            if field not in self.config:
                errors.append(f"Missing required field: {field}")
        return errors

    def _validate_urls(self) -> list[str]:
        """Validate URL fields.

        Returns:
            List of error messages for invalid URLs
        """
        errors = []
        source_url = self.config.get("source_url", "")
        if source_url and not (
            source_url.startswith("http://") or source_url.startswith("https://")
        ):
            errors.append(f"Invalid source_url: {source_url}")

        download_urls = self.config.get("download_urls", [])
        for url in download_urls:
            if not (url.startswith("http://") or url.startswith("https://")):
                errors.append(f"Invalid download URL: {url}")

        return errors
