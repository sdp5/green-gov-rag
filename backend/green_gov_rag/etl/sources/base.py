"""Base interface for document sources.

This module defines the core abstraction for document sources,
enabling a plugin-based architecture for adding new document types.

Includes optional MonitorableSource mixin for sources that support
automated monitoring and change detection.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from green_gov_rag.types import PDFClassificationResult

logger = logging.getLogger(__name__)


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
            Should include esg_metadata and spatial_metadata if present in config.
        """
        pass

    def _extract_structured_metadata(self) -> dict[str, Any]:
        """Extract esg_metadata, spatial_metadata, and parsing_strategy from config.

        Returns:
            Dictionary with esg_metadata, spatial_metadata, and parsing_strategy keys
        """
        metadata = {}

        # Extract ESG metadata if present
        if "esg_metadata" in self.config:
            metadata["esg_metadata"] = self.config["esg_metadata"]

        # Extract spatial metadata if present
        if "spatial_metadata" in self.config:
            metadata["spatial_metadata"] = self.config["spatial_metadata"]

        # Propagate parsing_strategy override so the chunking loop can use it
        if "parsing_strategy" in self.config:
            metadata["parsing_strategy"] = self.config["parsing_strategy"]

        return metadata

    @abstractmethod
    def get_document_id(self, url: str) -> str:
        """Generate unique document ID for delta indexing.

        This ID must be:
        - Stable: Same URL always generates same ID
        - Unique: Different documents have different IDs
        - Consistent: Monitoring and ingestion generate the same ID

        Args:
            url: Download URL for the document

        Returns:
            Unique document identifier (e.g., "federal_legislation_epbc_act")

        Example:
            >>> source.get_document_id("https://legislation.gov.au/epbc/2025.pdf")
            'federal_legislation_epbc_act_2025'
        """
        pass

    @abstractmethod
    def get_destination_path(self, url: str, base_dir: str = "data/raw") -> str:
        """Get local filesystem path for downloaded document.

        Creates hierarchical directory structure based on document metadata:
        {base_dir}/{jurisdiction}/{category}/{topic}/{filename}

        Args:
            url: Download URL for the document
            base_dir: Base directory for raw documents (default: data/raw)

        Returns:
            Full path where document should be saved

        Example:
            >>> source.get_destination_path("https://example.gov/doc.pdf")
            'data/raw/federal/legislation/biodiversity/epbc_act.pdf'
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
            "parsing_strategy",
        ]

    def get_parsing_strategy(self) -> PDFClassificationResult | None:
        """Return a forced parsing strategy for this document, or None to auto-classify.

        Reads 'parsing_strategy' from config. Valid values:
        - "fast": Force fast strategy (text-heavy, single-column PDFs)
        - "hi_res": Force hi_res strategy (complex layouts, tables)
        - "hi_res_vision": Force hi_res with image extraction (maps, diagrams)
        - "auto" or absent: Let the classifier decide per-document

        Returns:
            PDFClassificationResult with forced strategy, or None to auto-classify
        """
        from green_gov_rag.types import PDFClassificationResult, PDFParserStrategy

        raw = self.config.get("parsing_strategy")
        if raw is None:
            return None

        strategy_map: dict[str, tuple[PDFParserStrategy, bool] | None] = {
            "fast": (PDFParserStrategy.FAST, False),
            "hi_res": (PDFParserStrategy.HI_RES, False),
            "hi_res_vision": (PDFParserStrategy.HI_RES, True),
            "auto": None,
        }
        resolved = strategy_map.get(str(raw).lower())
        if resolved is None:
            return None

        strategy, extract_images = resolved
        return PDFClassificationResult(
            strategy=strategy,
            extract_images=extract_images,
            confidence=1.0,
            override_source="config",
        )

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

    def _generate_document_id(self, url: str) -> str:
        """Generate document ID from metadata and URL.

        Default implementation creates ID from:
        jurisdiction_category_topic_filename

        Subclasses can override for custom ID generation.

        Args:
            url: Download URL

        Returns:
            Document ID string
        """
        import hashlib
        import re
        from pathlib import Path
        from urllib.parse import urlparse

        # Extract metadata
        jurisdiction = self.config.get("jurisdiction", "unknown")
        category = self.config.get("category", "misc")
        topic = self.config.get("topic", "general")

        # Get filename from URL
        parsed = urlparse(url)
        filename = Path(parsed.path).stem

        # Clean and normalize
        parts = [jurisdiction, category, topic, filename]
        cleaned_parts = []
        for part in parts:
            # Remove special characters, convert to lowercase
            cleaned = re.sub(r"[^\w\s-]", "", part.lower())
            cleaned = re.sub(r"[-\s]+", "_", cleaned)
            cleaned_parts.append(cleaned)

        # Create ID
        doc_id = "_".join(cleaned_parts)

        # Add hash suffix if ID too long
        if len(doc_id) > 100:
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
            doc_id = doc_id[:90] + "_" + url_hash

        return doc_id

    def _generate_destination_path(self, url: str, base_dir: str = "data/raw") -> str:
        """Generate destination path from metadata and URL.

        Default implementation creates hierarchical structure:
        {base_dir}/{jurisdiction}/{category}/{topic}/{filename}

        Subclasses can override for custom directory structures.

        Args:
            url: Download URL
            base_dir: Base directory for raw documents

        Returns:
            Full path for downloaded file
        """
        import re
        from pathlib import Path
        from urllib.parse import urlparse

        # Extract metadata
        jurisdiction = self.config.get("jurisdiction", "unknown")
        category = self.config.get("category", "misc")
        topic = self.config.get("topic", "general")

        # Normalize directory names (replace spaces with underscores)
        jurisdiction = re.sub(r"[^\w\s-]", "", jurisdiction).replace(" ", "_")
        category = re.sub(r"[^\w\s-]", "", category).replace(" ", "_")
        topic = re.sub(r"[^\w\s-]", "", topic).replace(" ", "_")

        # Get filename from URL
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        if not filename:
            filename = "downloaded_file"

        # Build path
        dest_path = Path(base_dir) / jurisdiction / category / topic / filename

        return str(dest_path)


# ============================================================================
# Monitoring Plugin Architecture
# ============================================================================


@dataclass
class DiscoveredDocument:
    """A document discovered during automated monitoring.

    This represents a document found on a source website that may be
    new or updated compared to what we have in our database.
    """

    url: str
    title: str
    last_modified: datetime | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] | None = None
    file_size_bytes: int | None = None


@dataclass
class ChangeDetectionResult:
    """Result of checking if a document has changed.

    Used to determine whether we need to re-download and re-process a document.
    """

    has_changed: bool
    change_type: str | None = None  # 'new', 'updated', 'unchanged', 'deleted'
    old_hash: str | None = None
    new_hash: str | None = None
    confidence: float = 1.0  # 0-1, how confident we are in the change detection
    details: str | None = None


class MonitorableSource(ABC):
    """Mixin interface for sources that support automated monitoring.

    Sources can optionally implement this interface to enable:
    - Automated discovery of new documents via web scraping
    - Change detection to identify updated documents
    - Configurable monitoring schedules
    - Priority-based monitoring

    Example:
        >>> class CEREmissionsSource(DocumentSource, MonitorableSource):
        ...     async def discover_documents(self):
        ...         # Scrape CER website for PDFs
        ...         return [DiscoveredDocument(...)]
        ...
        ...     async def check_for_updates(self, known_document):
        ...         # Check if document changed
        ...         return ChangeDetectionResult(has_changed=False)
        ...
        ...     def get_monitoring_schedule(self):
        ...         return "0 2 * * *"  # Daily at 2am
    """

    async def check_url_alive(self, url: str) -> tuple[bool, int]:
        """Check if a URL is reachable via HTTP HEAD.

        Returns:
            (is_alive, http_status_code). is_alive is True for 2xx/3xx.
            Returns (False, 0) on network errors.
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url,
                    allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    return resp.status < 400, resp.status
        except Exception as exc:
            logger.debug("HEAD %s failed: %s", url, exc)
            return False, 0

    async def discover_documents(self) -> list[DiscoveredDocument]:
        """Default: return documents from config download_urls.

        Sources that scrape websites (e.g. CEREmissionsSource) override this.
        Static URL sources (federal/state/local) use this default.

        TODO: Future enhancement — when a URL is dead (404), fetch the source_url
        HTML page and use an LLM agent to parse it for a replacement download link.
        Government pages often contain "This document has been replaced by..." notices
        or updated PDF links that could be extracted automatically.

        Returns:
            List of DiscoveredDocument, one per download_url in config.
        """
        config: dict[str, Any] = getattr(self, "config", {})
        urls: list[str] = config.get("download_urls", [])
        title: str = config.get("title", "")
        return [DiscoveredDocument(url=url, title=title) for url in urls]

    async def check_for_updates(
        self, known_document: dict[str, Any]
    ) -> ChangeDetectionResult:
        """Default: HEAD request to detect 404 (dead URL) or content changes.

        Strategy:
          1. HEAD the URL — if 404 → deleted (signal: url_dead, not superseded).
          2. Compare Last-Modified header if available (confidence 0.9).
          3. Partial content hash (first 64 KB) as fallback (confidence 1.0).

        Sources with richer detection (ETag, scraping) override this.

        Args:
            known_document: Dict with keys url, content_hash, last_checked, metadata.

        Returns:
            ChangeDetectionResult
        """
        import aiohttp

        url: str = known_document.get("url", "")
        known_hash: str | None = known_document.get("content_hash")

        try:
            async with aiohttp.ClientSession() as session:
                # Step 1 — HEAD for liveness + Last-Modified
                async with session.head(
                    url,
                    allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as head_resp:
                    status = head_resp.status

                    if status == 404:
                        return ChangeDetectionResult(
                            has_changed=True,
                            change_type="deleted",
                            confidence=1.0,
                            details="HTTP 404 — URL is dead",
                        )

                    if status >= 400:
                        # Transient error — don't act on it
                        return ChangeDetectionResult(
                            has_changed=False,
                            change_type="unchanged",
                            confidence=0.3,
                            details=f"HTTP {status} — treating as unchanged",
                        )

                    # Step 2 — Last-Modified header
                    last_modified_str = head_resp.headers.get("Last-Modified")
                    if last_modified_str:
                        try:
                            from email.utils import parsedate_to_datetime

                            remote_dt = parsedate_to_datetime(last_modified_str)
                            local_dt = known_document.get("last_checked")
                            if local_dt and remote_dt > local_dt:
                                return ChangeDetectionResult(
                                    has_changed=True,
                                    change_type="updated",
                                    confidence=0.9,
                                    details=f"Last-Modified changed: {last_modified_str}",
                                )
                        except Exception:
                            pass  # Fall through to hash check

                # Step 3 — partial content hash (first 64 KB)
                if known_hash:
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as get_resp:
                        chunk = await get_resp.content.read(65536)
                        new_hash = hashlib.sha256(chunk).hexdigest()
                        if new_hash != known_hash:
                            return ChangeDetectionResult(
                                has_changed=True,
                                change_type="updated",
                                new_hash=new_hash,
                                old_hash=known_hash,
                                confidence=1.0,
                                details="Content hash changed (first 64 KB)",
                            )

        except Exception as exc:
            logger.warning("check_for_updates failed for %s: %s", url, exc)
            return ChangeDetectionResult(
                has_changed=False,
                change_type="unchanged",
                confidence=0.0,
                details=f"Error: {exc}",
            )

        return ChangeDetectionResult(has_changed=False, change_type="unchanged")

    def get_monitoring_schedule(self) -> str:
        """Get cron expression for monitoring schedule.

        Returns:
            Cron expression (default: daily at 2am)

        Common schedules:
            - "0 2 * * *": Daily at 2am
            - "0 */6 * * *": Every 6 hours
            - "0 2 * * 1": Weekly on Monday at 2am
            - "0 2 1 * *": Monthly on 1st at 2am
        """
        return "0 2 * * *"  # Daily at 2am

    def get_monitoring_priority(self) -> str:
        """Get monitoring priority for this source.

        Higher priority sources are checked more frequently and
        processed first when changes are detected.

        Returns:
            Priority level: 'high', 'medium', or 'low'

        Guidelines:
            - high: Critical regulatory documents (NGER, ISSB guidelines)
            - medium: Important policy documents
            - low: Reference materials, older legislation
        """
        return "medium"

    def is_monitorable(self) -> bool:
        """Check if this source instance supports monitoring.

        Can be overridden to disable monitoring for specific instances
        (e.g., one-off historical documents).

        Returns:
            True if monitoring is enabled for this instance
        """
        return True
