"""Base interface for document sources.

This module defines the core abstraction for document sources,
enabling a plugin-based architecture for adding new document types.

Includes optional MonitorableSource mixin for sources that support
automated monitoring and change detection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from green_gov_rag.types import PDFClassificationResult


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

    @abstractmethod
    async def discover_documents(self) -> list[DiscoveredDocument]:
        """Discover documents by scraping/crawling the source website.

        This method should scrape the source's website to find all available
        documents (PDFs, HTML pages, etc.) and return metadata about them.

        Returns:
            List of discovered documents with URLs and metadata

        Example:
            >>> async def discover_documents(self):
            ...     async with aiohttp.ClientSession() as session:
            ...         async with session.get(self.GUIDELINES_URL) as response:
            ...             soup = BeautifulSoup(await response.text(), 'html.parser')
            ...             pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))
            ...             return [
            ...                 DiscoveredDocument(
            ...                     url=link['href'],
            ...                     title=link.text.strip(),
            ...                     metadata={'source': 'CER Guidelines'}
            ...                 )
            ...                 for link in pdf_links
            ...             ]
        """
        pass

    @abstractmethod
    async def check_for_updates(
        self, known_document: dict[str, Any]
    ) -> ChangeDetectionResult:
        """Check if a known document has been updated.

        Given a document we already have in our database, check if the
        source has published an updated version.

        Args:
            known_document: Dictionary with document metadata including:
                - url: Document URL
                - content_hash: SHA256 hash of current content
                - last_checked: When we last checked for updates
                - metadata: Additional metadata

        Returns:
            ChangeDetectionResult indicating if document changed

        Example:
            >>> async def check_for_updates(self, known_document):
            ...     url = known_document['url']
            ...     async with aiohttp.ClientSession() as session:
            ...         async with session.head(url) as response:
            ...             last_modified = response.headers.get('Last-Modified')
            ...             if last_modified:
            ...                 remote_date = datetime.strptime(
            ...                     last_modified, '%a, %d %b %Y %H:%M:%S %Z'
            ...                 )
            ...                 local_date = known_document.get('last_modified')
            ...                 if remote_date > local_date:
            ...                     return ChangeDetectionResult(
            ...                         has_changed=True,
            ...                         change_type='updated',
            ...                         confidence=0.9,
            ...                     )
            ...     return ChangeDetectionResult(has_changed=False, change_type='unchanged')
        """
        pass

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
