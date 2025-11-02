---
name: Add Document Source
about: Add a new government document to the configuration (with optional monitoring)
title: 'Add [Document Name] to document sources'
labels: 'good first issue, documentation, help wanted'
assignees: ''
---

## 📄 Add Document Source: [Document Name]

**Complexity:** 🟢 Good First Issue (Static) / 🟡 Medium (With Monitoring)
**Estimated Time:** 30-60 minutes (Static) / 2-4 hours (With Monitoring)
**Skills Required:**
- **Static config:** YAML, basic understanding of Australian government documents
- **With monitoring:** Python, async/await, web scraping (BeautifulSoup, aiohttp)

---

### 📋 What to do

Add the following document to the project's document configuration:

**Document:** [Full document title]
**Source:** [URL to official source]
**Jurisdiction:** [federal / state / local]
**Category:** [legislation / regulation / guideline / policy]
**Topic:** [e.g., emissions_reporting, biodiversity, planning]

**Choose one approach:**

1. **🟢 Static Configuration** (Good First Issue)
   - Add document entry to `configs/documents_config.yml`
   - Suitable for one-off documents or when source doesn't update frequently

2. **🟡 With Monitoring** (Medium - Recommended for regulatory sources)
   - Create custom DocumentSource class implementing `MonitorableSource`
   - Enables automated discovery and change detection
   - See reference implementation: `green_gov_rag/etl/sources/cer_emissions.py`

### ✅ Acceptance Criteria

**For Static Configuration:**
- [ ] Document entry added to `configs/documents_config.yml`
- [ ] All required fields populated correctly
- [ ] Download URLs are valid and publicly accessible
- [ ] Configuration validates without errors
- [ ] Document loads successfully via `load_document_sources()`

**Additional for Monitoring Support:**
- [ ] Custom source class created in `green_gov_rag/etl/sources/`
- [ ] Implements `MonitorableSource` mixin interface
- [ ] `get_document_id()` method implemented (for delta indexing)
- [ ] `get_destination_path()` method implemented (for file storage)
- [ ] `discover_documents()` method scrapes source website
- [ ] `check_for_updates()` method detects changes
- [ ] Monitoring schedule and priority configured
- [ ] Unit tests added in `tests/etl/sources/`
- [ ] Tested with monitoring service

### 📝 Steps to Complete

---

## Option 1: Static Configuration (🟢 Good First Issue)

#### 1. Add Document Configuration

Edit `configs/documents_config.yml` and add:

```yaml
- title: [Document Title]
  source_url: [Official source URL]
  download_urls:
    - [URL to PDF/HTML document]
  jurisdiction: [federal/state/local]
  category: [category]
  topic: [topic]
  region: [Region name]
  sovereign: true
```

**Tip:** Look at existing entries in the file for examples matching your document type.

#### 2. Determine Required Metadata

Depending on document type, you may need to add:

**For emissions/ESG documents:**
```yaml
  esg_metadata:
    frameworks: [NGER, GHG_Protocol, ISSB]
    emission_scopes: [scope_1, scope_2, scope_3]
    greenhouse_gases: [CO2, CH4, N2O]
    reportable_under_nger: true/false
```

**For state/local documents:**
```yaml
  spatial_metadata:
    spatial_scope: state  # or 'local'
    state: NSW  # or VIC, QLD, SA, WA, TAS, NT, ACT
    lga_codes: []  # for local documents: [40070]
    lga_names: []  # for local documents: ["City of Adelaide"]
    applies_to_all_lgas: true  # false for local documents
```

#### 3. Validate Your Configuration

Run the validation test:

```bash
python -c "
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    if '[Document Name]' in source.config.get('title', ''):
        validation = source.validate()
        print(f'Valid: {validation.is_valid}')
        if not validation.is_valid:
            print(f'Errors: {validation.errors}')
            print(f'Warnings: {validation.warnings}')
        else:
            print(f'Metadata: {source.get_metadata()}')
            print(f'URLs: {source.get_download_urls()}')
"
```

#### 4. Submit Pull Request

Create a PR with:
- **Title:** `Add [Document Name] to document sources`
- **Description:** Brief description of the document and why it's relevant
- **Files changed:** `configs/documents_config.yml`

---

## Option 2: With Monitoring Support (🟡 Medium)

**Recommended for:** Regulatory sources that update frequently (e.g., EPA guidelines, CER documents)

**Reference Implementation:** See `green_gov_rag/etl/sources/cer_emissions.py`

### Step 1: Create Source Class

Create new file `green_gov_rag/etl/sources/[your_source].py`:

```python
"""[Source Name] document source with monitoring support."""

from __future__ import annotations

import aiohttp
from bs4 import BeautifulSoup

from green_gov_rag.etl.sources.base import (
    ChangeDetectionResult,
    DiscoveredDocument,
    MonitorableSource,
)
from green_gov_rag.etl.sources.[base_type] import [BaseSourceClass]


class [YourSource]Source([BaseSourceClass], MonitorableSource):
    """[Source Name] with automated monitoring.

    Features:
    - Web scraping to discover new documents
    - Change detection via HTTP headers and content hashing
    - [Monitoring schedule] monitoring
    - [Priority] priority
    - Consistent document ID generation (for delta indexing)
    """

    # Website URLs to scrape
    GUIDELINES_URL = "https://..."

    def get_document_id(self, url: str) -> str:
        """Generate unique document ID for delta indexing.

        This ID MUST be consistent between monitoring and ingestion!
        Uses default implementation from base class unless you need custom logic.

        Returns:
            Document ID like "federal_legislation_epbc_act_2025"
        """
        return self._generate_document_id(url)  # Use base class default

    def get_destination_path(self, url: str, base_dir: str = "data/raw") -> str:
        """Get filesystem path for downloaded document.

        Creates hierarchical structure: {base_dir}/{jurisdiction}/{category}/{topic}/{filename}
        Uses default implementation from base class unless you need custom logic.

        Returns:
            Full path where file should be saved
        """
        return self._generate_destination_path(url, base_dir)  # Use base class default

    async def discover_documents(self) -> list[DiscoveredDocument]:
        """Discover documents by scraping [source] website.

        Returns:
            List of discovered documents with metadata
        """
        discovered = []

        async with aiohttp.ClientSession() as session:
            async with session.get(self.GUIDELINES_URL) as response:
                if response.status != 200:
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find PDF/HTML links
                links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))

                for link in links:
                    href = link.get('href', '')
                    title = link.get_text(strip=True)

                    # Make absolute URL if needed
                    if not href.startswith('http'):
                        href = f"https://... + {href}"

                    discovered.append(
                        DiscoveredDocument(
                            url=href,
                            title=title,
                            metadata=self._extract_metadata(title),
                        )
                    )

        return discovered

    async def check_for_updates(
        self,
        known_document: dict
    ) -> ChangeDetectionResult:
        """Check if document has been updated.

        Strategy:
        1. Check Last-Modified HTTP header (fast)
        2. Check ETag header (fast)
        3. Fall back to content hash (slow but definitive)

        Args:
            known_document: Dictionary with url, content_hash, etc.

        Returns:
            ChangeDetectionResult indicating if changed
        """
        url = known_document['url']

        async with aiohttp.ClientSession() as session:
            # Try HEAD request first
            async with session.head(url) as response:
                if response.status == 200:
                    # Check Last-Modified header
                    last_modified = response.headers.get('Last-Modified')
                    if last_modified:
                        # Parse and compare with known_document['last_modified']
                        # Return ChangeDetectionResult appropriately
                        pass

            # Fall back to content hash if needed
            # ... (see CEREmissionsSource for full implementation)

        return ChangeDetectionResult(
            has_changed=False,
            change_type='unchanged',
            confidence=1.0,
        )

    def get_monitoring_schedule(self) -> str:
        """Monitoring schedule (cron expression).

        Returns:
            "0 2 * * *"  # Daily at 2am
            "0 */6 * * *"  # Every 6 hours (high priority)
            "0 2 * * 1"  # Weekly on Monday
        """
        return "0 2 * * *"  # Daily

    def get_monitoring_priority(self) -> str:
        """Monitoring priority.

        Returns:
            'high' - Critical regulatory documents (NGER, ISSB)
            'medium' - Important policy documents
            'low' - Reference materials
        """
        return "medium"

    def _extract_metadata(self, title: str) -> dict:
        """Extract metadata from document title."""
        # Parse title for emission scopes, frameworks, etc.
        return {
            "regulator": "[Source Name]",
            # Add other metadata...
        }
```

### Step 2: Add Config Entry (Optional)

If you want static fallback URLs, add to `configs/documents_config.yml`:

```yaml
- title: [Source Name] - [Document Type]
  source_url: https://...
  jurisdiction: [federal/state/local]
  category: [category]
  topic: [topic]
  # Note: download_urls are optional when monitoring is enabled
  # The source will discover documents automatically
```

### Step 3: Add Unit Tests

Create `tests/etl/sources/test_[your_source].py`:

```python
"""Tests for [YourSource]."""

import pytest
from green_gov_rag.etl.sources.[your_source] import [YourSource]Source


@pytest.mark.asyncio
async def test_discover_documents():
    """Test document discovery."""
    source = [YourSource]Source(config={
        'title': 'Test Source',
        'jurisdiction': 'federal',
        'category': 'environment',
        'topic': 'test',
    })

    discovered = await source.discover_documents()

    assert len(discovered) > 0
    assert all(d.url.startswith('http') for d in discovered)


@pytest.mark.asyncio
async def test_check_for_updates():
    """Test change detection."""
    source = [YourSource]Source(config={})

    known_doc = {
        'url': 'https://...',
        'content_hash': 'abc123',
    }

    result = await source.check_for_updates(known_doc)

    assert result.change_type in ['new', 'updated', 'unchanged']
    assert 0 <= result.confidence <= 1.0
```

### Step 4: Test with Monitoring Service

```python
# Test in Python REPL or script
import asyncio
from green_gov_rag.api.services.monitoring_service import MonitoringService

async def test_monitoring():
    service = MonitoringService()
    result = await service.monitor_source('[your_source]')
    print(result)

asyncio.run(test_monitoring())
```

### Step 5: Submit Pull Request

Create a PR with:
- **Title:** `Add [Source Name] with monitoring support`
- **Description:**
  - What source you added
  - What documents it monitors
  - Monitoring schedule and priority
  - Testing evidence (screenshots/logs)
- **Files changed:**
  - `green_gov_rag/etl/sources/[your_source].py` (new)
  - `tests/etl/sources/test_[your_source].py` (new)
  - `configs/documents_config.yml` (optional)

---

### 📚 Resources

**General:**
- **Contributing Guide:** [CONTRIBUTING_DOCUMENT_SOURCES.md](../../docs/CONTRIBUTING_DOCUMENT_SOURCES.md)
- **Example Configs:** Check existing entries in `configs/documents_config.yml`

**For Static Configuration:**
- **Plugin Types:**
  - Federal legislation → `FederalLegislationSource`
  - Emissions reporting → `EmissionsReportingSource`
  - State legislation → `StateLegislationSource`
  - Local government → `LocalGovernmentSource`

**For Monitoring Support:**
- **Reference Implementation:** `green_gov_rag/etl/sources/cer_emissions.py` (complete example)
- **Architecture Guide:** [MONITORING_PLUGIN_ARCHITECTURE.md](../../backend/docs/MONITORING_PLUGIN_ARCHITECTURE.md)
- **Implementation Summary:** [MONITORING_IMPLEMENTATION_SUMMARY.md](../../backend/docs/MONITORING_IMPLEMENTATION_SUMMARY.md)
- **MonitorableSource Interface:** `green_gov_rag/etl/sources/base.py` (lines 196-325)

### 🆘 Need Help?

- **YAML syntax:** Check the [example configs](../../configs/documents_config.yml)
- **Metadata fields:** See [CONTRIBUTING_DOCUMENT_SOURCES.md](../../docs/CONTRIBUTING_DOCUMENT_SOURCES.md)
- **Web scraping:** Check [CEREmissionsSource](../../backend/green_gov_rag/etl/sources/cer_emissions.py) reference
- **Testing:** See existing test files in `tests/etl/sources/`
- **Questions:** Comment on this issue!

---

## 🎯 Examples

### Example 1: Static Configuration (Federal Legislation)

```yaml
- title: National Greenhouse and Energy Reporting Act 2007
  source_url: https://www.legislation.gov.au/Series/C2007A00175
  download_urls:
    - https://www.legislation.gov.au/C2007A00175/latest/downloads/C2007A00175.pdf
  jurisdiction: federal
  category: legislation
  topic: emissions_reporting
  region: Australia
  sovereign: true
  esg_metadata:
    frameworks: [NGER]
    emission_scopes: [scope_1, scope_2]
    reportable_under_nger: true
  spatial_metadata:
    spatial_scope: federal
    state: null
    applies_to_all_lgas: true
    applies_to_point: false
```

### Example 2: With Monitoring (CER Emissions Source)

**File:** `green_gov_rag/etl/sources/cer_emissions.py`

See full implementation for reference. Key highlights:

```python
class CEREmissionsSource(EmissionsReportingSource, MonitorableSource):
    """Clean Energy Regulator with automated monitoring."""

    NGER_GUIDELINES_URL = "https://cer.gov.au/schemes/nger/..."

    async def discover_documents(self):
        # Scrapes CER website for NGER and Safeguard guidelines
        # Returns list of DiscoveredDocument

    async def check_for_updates(self, known_document):
        # Multi-strategy change detection:
        # 1. Last-Modified header (90% confidence)
        # 2. ETag header (95% confidence)
        # 3. Content hash (100% confidence)

    def get_monitoring_schedule(self):
        return "0 2 * * *"  # Daily at 2am

    def get_monitoring_priority(self):
        return "high"  # Critical regulatory documents
```

**Benefits:**
- ✅ Automatically discovers new CER guidelines
- ✅ Detects updates to existing documents
- ✅ Triggers ETL pipeline when changes found
- ✅ Tracks version history
- ✅ High priority monitoring (daily checks)

---

**Ready to contribute?** Choose your approach and submit your PR! 🚀

**Questions?** Feel free to ask in the comments below.
