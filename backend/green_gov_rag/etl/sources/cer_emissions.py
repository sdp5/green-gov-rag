"""Clean Energy Regulator (CER) emissions source with monitoring.

This is a reference implementation showing how to extend DocumentSource
with MonitorableSource for automated document discovery and change detection.

Key features:
- Web scraping to discover new CER guidelines
- Change detection via HTTP headers and content hashing
- Configurable monitoring schedule (daily)
- High priority for regulatory compliance documents
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from green_gov_rag.etl.sources.base import (
    ChangeDetectionResult,
    DiscoveredDocument,
    MonitorableSource,
)
from green_gov_rag.etl.sources.emissions import EmissionsReportingSource


class CEREmissionsSource(EmissionsReportingSource, MonitorableSource):
    """Clean Energy Regulator emissions reporting source with monitoring.

    This source:
    - Extends EmissionsReportingSource for static ETL processing
    - Implements MonitorableSource for automated monitoring
    - Scrapes CER website for new/updated guidelines
    - Detects changes via Last-Modified headers and content hashing

    Example config:
        title: Clean Energy Regulator - Emissions Guidelines
        source_url: https://cer.gov.au/schemes/nger/reporting/published-information
        jurisdiction: federal
        category: environment
        topic: emissions_reporting
        esg_metadata:
          frameworks: [NGER, GHG_Protocol]
          regulator: Clean Energy Regulator
          reportable_under_nger: true
    """

    # CER website URLs for scraping
    NGER_GUIDELINES_URL = "https://cer.gov.au/schemes/nger/reporting/published-information/guidelines-and-resources"
    SAFEGUARD_GUIDELINES_URL = (
        "https://cer.gov.au/schemes/safeguard-mechanism/guidelines-and-resources"
    )

    def __init__(self, config: dict[str, Any]):
        """Initialize CER emissions source.

        Args:
            config: Document configuration dictionary
        """
        super().__init__(config)

        # Set default regulator if not specified
        esg_metadata = self.config.get("esg_metadata", {})
        if "regulator" not in esg_metadata:
            esg_metadata["regulator"] = "Clean Energy Regulator"
            self.config["esg_metadata"] = esg_metadata

    # ========================================================================
    # MonitorableSource Implementation
    # ========================================================================

    async def discover_documents(self) -> list[DiscoveredDocument]:
        """Discover CER guidelines by scraping their website.

        Scrapes both NGER and Safeguard Mechanism pages for PDF guidelines.

        Returns:
            List of discovered documents with metadata
        """
        discovered = []

        # Scrape NGER guidelines
        nger_docs = await self._scrape_guidelines_page(
            self.NGER_GUIDELINES_URL, source_type="NGER"
        )
        discovered.extend(nger_docs)

        # Scrape Safeguard Mechanism guidelines
        safeguard_docs = await self._scrape_guidelines_page(
            self.SAFEGUARD_GUIDELINES_URL, source_type="Safeguard"
        )
        discovered.extend(safeguard_docs)

        return discovered

    async def check_for_updates(
        self, known_document: dict[str, Any]
    ) -> ChangeDetectionResult:
        """Check if a known CER document has been updated.

        Uses HTTP HEAD request to check Last-Modified header, then
        falls back to content hash comparison if needed.

        Args:
            known_document: Dictionary with:
                - url: Document URL
                - content_hash: SHA256 hash of current content
                - last_checked: When we last checked
                - metadata: Additional metadata

        Returns:
            ChangeDetectionResult indicating if document changed
        """
        url = known_document["url"]
        known_hash = known_document.get("content_hash")

        try:
            async with aiohttp.ClientSession() as session:
                # First, try HEAD request to check Last-Modified
                async with session.head(url, allow_redirects=True) as response:
                    if response.status != 200:
                        return ChangeDetectionResult(
                            has_changed=False,
                            change_type="unchanged",
                            confidence=0.5,
                            details=f"HTTP {response.status} - cannot determine",
                        )

                    # Check Last-Modified header
                    last_modified_str = response.headers.get("Last-Modified")
                    if last_modified_str:
                        try:
                            remote_date = datetime.strptime(
                                last_modified_str, "%a, %d %b %Y %H:%M:%S %Z"
                            )
                            local_date = known_document.get("last_modified")

                            if local_date and remote_date > local_date:
                                return ChangeDetectionResult(
                                    has_changed=True,
                                    change_type="updated",
                                    confidence=0.9,
                                    details=f"Last-Modified: {last_modified_str}",
                                )
                        except ValueError:
                            # Failed to parse date, fall back to content hash
                            pass

                    # Check ETag header
                    etag = response.headers.get("ETag")
                    known_etag = known_document.get("metadata", {}).get("etag")
                    if etag and known_etag and etag != known_etag:
                        return ChangeDetectionResult(
                            has_changed=True,
                            change_type="updated",
                            confidence=0.95,
                            details=f"ETag changed: {known_etag} -> {etag}",
                        )

                # Fall back to content hash comparison
                # Download first 64KB to compute partial hash (faster)
                async with session.get(url) as response:
                    if response.status != 200:
                        return ChangeDetectionResult(
                            has_changed=False,
                            change_type="unchanged",
                            confidence=0.5,
                            details=f"HTTP {response.status}",
                        )

                    # Read first chunk for quick hash
                    chunk = await response.content.read(65536)  # 64KB
                    partial_hash = hashlib.sha256(chunk).hexdigest()

                    # If known hash starts with this, likely unchanged
                    if known_hash and known_hash.startswith(partial_hash[:16]):
                        return ChangeDetectionResult(
                            has_changed=False,
                            change_type="unchanged",
                            confidence=0.8,
                            details="Content hash match (partial)",
                        )

                    # Compute full hash
                    hasher = hashlib.sha256(chunk)
                    while True:
                        chunk = await response.content.read(65536)
                        if not chunk:
                            break
                        hasher.update(chunk)

                    full_hash = hasher.hexdigest()

                    if known_hash and full_hash != known_hash:
                        return ChangeDetectionResult(
                            has_changed=True,
                            change_type="updated",
                            old_hash=known_hash,
                            new_hash=full_hash,
                            confidence=1.0,
                            details="Content hash changed",
                        )

                    return ChangeDetectionResult(
                        has_changed=False,
                        change_type="unchanged",
                        confidence=1.0,
                        details="Content hash unchanged",
                    )

        except Exception as e:
            return ChangeDetectionResult(
                has_changed=False,
                change_type="unchanged",
                confidence=0.0,
                details=f"Error checking updates: {e}",
            )

    def get_monitoring_schedule(self) -> str:
        """Get monitoring schedule for CER documents.

        CER guidelines are critical regulatory documents, so we check daily.

        Returns:
            Cron expression: daily at 2am
        """
        return "0 2 * * *"  # Daily at 2am

    def get_monitoring_priority(self) -> str:
        """Get monitoring priority for CER documents.

        Returns:
            'high' - CER guidelines are critical for compliance
        """
        return "high"

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _scrape_guidelines_page(
        self, url: str, source_type: str
    ) -> list[DiscoveredDocument]:
        """Scrape a CER guidelines page for PDF documents.

        Args:
            url: URL of guidelines page
            source_type: 'NGER' or 'Safeguard' for metadata

        Returns:
            List of discovered documents
        """
        discovered = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find all PDF links
                    pdf_links = soup.find_all(
                        "a", href=lambda x: x and x.lower().endswith(".pdf")
                    )

                    for link in pdf_links:
                        href_raw = link.get("href", "")

                        # Ensure href is a string
                        if not isinstance(href_raw, str):
                            continue

                        href: str = href_raw

                        # Make absolute URL
                        if not href.startswith("http"):
                            base_url = "https://cer.gov.au"
                            href = base_url + href if href.startswith("/") else href

                        # Extract title from link text
                        title = link.get_text(strip=True)

                        # Extract metadata from title/URL
                        metadata = self._extract_metadata_from_title(title, source_type)

                        discovered.append(
                            DiscoveredDocument(
                                url=href,
                                title=title,
                                metadata=metadata,
                            )
                        )

        except Exception as e:
            # Log error but don't fail - return empty list
            print(f"Error scraping {url}: {e}")

        return discovered

    def _extract_metadata_from_title(
        self, title: str, source_type: str
    ) -> dict[str, Any]:
        """Extract ESG metadata from document title.

        Args:
            title: Document title
            source_type: 'NGER' or 'Safeguard'

        Returns:
            Metadata dictionary with ESG fields
        """
        metadata: dict[str, Any] = {
            "regulator": "Clean Energy Regulator",
            "frameworks": [],
            "emission_scopes": [],
        }

        # Add framework based on source type
        if source_type == "NGER":
            metadata["frameworks"].append("NGER")
            metadata["reportable_under_nger"] = True
        elif source_type == "Safeguard":
            metadata["frameworks"].append("Safeguard_Mechanism")

        # Extract emission scopes from title
        title_lower = title.lower()

        if "scope 1" in title_lower or "scope1" in title_lower:
            metadata["emission_scopes"].append("scope_1")
        if "scope 2" in title_lower or "scope2" in title_lower:
            metadata["emission_scopes"].append("scope_2")
        if "scope 3" in title_lower or "scope3" in title_lower:
            metadata["emission_scopes"].append("scope_3")

        # Extract greenhouse gases
        gases = []
        if re.search(r"\\bco2\\b", title_lower):
            gases.append("CO2")
        if re.search(r"\\bch4\\b|methane", title_lower):
            gases.append("CH4")
        if re.search(r"\\bn2o\\b|nitrous oxide", title_lower):
            gases.append("N2O")

        if gases:
            metadata["greenhouse_gases"] = gases

        # Extract sector/activity if present
        sectors = {
            "coal": "coal_mining",
            "oil": "oil_and_gas",
            "gas": "oil_and_gas",
            "electricity": "electricity_generation",
            "power": "electricity_generation",
            "transport": "transport",
            "agriculture": "agriculture",
            "waste": "waste",
            "industrial": "industrial_processes",
        }

        for keyword, sector in sectors.items():
            if keyword in title_lower:
                metadata["sector"] = sector
                break

        return metadata


# ============================================================================
# Example: How Community Contributors Would Add New Sources
# ============================================================================

"""
GOOD FIRST ISSUE TEMPLATE:

Title: Add monitoring support for [Source Name]

Description:
Add automated monitoring capabilities for [Source Name] documents.

Requirements:
1. Create a new class inheriting from both DocumentSource and MonitorableSource
2. Implement discover_documents() to scrape [website URL]
3. Implement check_for_updates() using HTTP headers or content hashing
4. Set appropriate monitoring schedule and priority
5. Add unit tests

Example:
```python
class MyNewSource(DocumentSource, MonitorableSource):
    async def discover_documents(self):
        # Scrape website for documents
        pass

    async def check_for_updates(self, known_document):
        # Check if document changed
        pass

    def get_monitoring_schedule(self):
        return "0 2 * * *"  # Daily

    def get_monitoring_priority(self):
        return "medium"
```

See CEREmissionsSource as reference implementation.

Skills needed:
- Python (async/await)
- Web scraping (BeautifulSoup, aiohttp)
- Basic understanding of HTTP headers

Difficulty: Medium
Good first issue: Yes
"""
