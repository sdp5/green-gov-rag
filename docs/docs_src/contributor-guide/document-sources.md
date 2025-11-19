# Adding Document Sources

> Contribute to GreenGovRAG by adding new Australian regulatory documents

## Overview

GreenGovRAG uses a **plugin-based architecture** to support different types of government documents. You can contribute by adding new document sources in two ways:

1. **🟢 Static Configuration** (Good First Issue) - Add entries to YAML config
2. **🟡 With Monitoring** (Medium) - Create custom source class with automated discovery

## Quick Decision Guide

| Choose Static Configuration if... | Choose With Monitoring if... |
|-----------------------------------|------------------------------|
| ✅ One-off historical document | ✅ Regulatory source that updates frequently |
| ✅ Source doesn't change often | ✅ Need automated change detection |
| ✅ Manual URLs are acceptable | ✅ Want to discover new documents automatically |
| ✅ First time contributing | ✅ Comfortable with Python async/await |
| **⏱️ 30-60 minutes** | **⏱️ 2-4 hours** |

---

## Option 1: Static Configuration (Good First Issue)

### Step 1: Understand the Config Structure

Documents are configured in `backend/configs/documents_config.yml`. Each entry requires:

**Required fields:**

- `title` - Official document name
- `jurisdiction` - `federal`, `state`, or `local`
- `category` - `legislation`, `regulation`, `guideline`, `building`, `environment`, etc.
- `topic` - Subject area (e.g., `biodiversity`, `emissions_reporting`, `planning`)
- `region` - Geographic region
- `sovereign` - Boolean, typically `true` for Australian documents

**Optional fields:**

- `source_url` - Official webpage for the document
- `download_urls` - Array of direct download links
- `esg_metadata` - ESG/emissions metadata (see below)
- `spatial_metadata` - Geospatial metadata (see below)

### Step 2: Choose Your Document Type

GreenGovRAG automatically selects the appropriate plugin based on your metadata:

#### Federal Legislation

```yaml
- title: Environment Protection and Biodiversity Conservation Act 1999
  source_url: https://www.legislation.gov.au/Series/C2004A00485
  download_urls:
    - https://www.legislation.gov.au/C2004A00485/latest/downloads/C2004A00485.pdf
  jurisdiction: federal
  category: legislation
  topic: biodiversity
  region: Australia
  sovereign: true
  spatial_metadata:
    spatial_scope: federal
    state: null
    lga_codes: []
    lga_names: []
    applies_to_all_lgas: true
    applies_to_point: false
```

#### Emissions Reporting

```yaml
- title: Clean Energy Regulator - Scope 1 Coal Mining Guideline
  source_url: https://cer.gov.au/
  download_urls:
    - https://cer.gov.au/document/estimating-emissions-and-energy-coal-mining-guideline
  jurisdiction: federal
  category: environment
  topic: emissions_reporting
  region: Australia
  sovereign: true
  esg_metadata:
    frameworks: [NGER, GHG_Protocol]
    measurement_standard: GHG_Protocol_Corporate_Standard
    emission_scopes: [scope_1]
    greenhouse_gases: [CO2, CH4, N2O]
    consolidation_method: operational_control
    methodology_type: calculation
    reportable_under_nger: true
    regulator: Clean Energy Regulator
    regulation_type: guideline
    activity_types: [fuel_combustion, fugitive_emissions]
    facility_types: [coal_mine]
    industry_codes: [B0600]  # ANZSIC code
  spatial_metadata:
    spatial_scope: federal
    applies_to_all_lgas: true
```

#### State Legislation

```yaml
- title: NSW Environmental Planning and Assessment Act 1979
  source_url: https://legislation.nsw.gov.au/view/html/inforce/current/act-1979-203
  download_urls:
    - https://legislation.nsw.gov.au/.../act-1979-203.pdf
  jurisdiction: state
  category: legislation
  topic: planning
  region: New South Wales
  sovereign: true
  spatial_metadata:
    spatial_scope: state
    state: NSW
    lga_codes: []
    lga_names: []
    applies_to_all_lgas: false  # State-specific
    applies_to_point: false
```

#### Local Government

```yaml
- title: City of Adelaide Development Plan
  source_url: https://www.cityofadelaide.com.au/planning-development/
  download_urls:
    - https://www.cityofadelaide.com.au/.../development-plan.pdf
  jurisdiction: local
  category: planning
  topic: development_control
  region: South Australia
  sovereign: true
  spatial_metadata:
    spatial_scope: local
    state: SA
    lga_codes: [40070]  # ABS LGA code
    lga_names: ["City of Adelaide"]
    applies_to_all_lgas: false
    applies_to_point: false
```

### Step 3: Add Your Configuration

1. **Edit the config file:**
   ```bash
   cd backend
   nano configs/documents_config.yml
   ```

2. **Add your entry** following the appropriate template above

3. **Save and validate** (see Step 4 below)

### Step 4: Validate Your Configuration

Run validation to ensure your config is correct:

```bash
cd backend
python -c "
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    if 'Your Document Title' in source.config.get('title', ''):
        result = source.validate()
        if result.is_valid:
            print('✅ Valid configuration')
            print(f'Metadata: {source.get_metadata()}')
            print(f'URLs: {source.get_download_urls()}')
        else:
            print('❌ Validation failed')
            print(f'Errors: {result.errors}')
            print(f'Warnings: {result.warnings}')
"
```

### Step 5: Test Document Loading

Optional but recommended - test that the document can be ingested:

```bash
# Run ETL pipeline for your specific source
greengovrag-cli etl run-pipeline \
  --config configs/documents_config.yml \
  --filter-source "Your Document Title"
```

### Step 6: Submit Pull Request

Create a PR with:

- **Title:** `Add [Document Name] to document sources`
- **Description:** Brief explanation of the document and why it's relevant
- **Files changed:** `backend/configs/documents_config.yml`
- **Label:** `good first issue, documentation`

---

## Option 2: With Monitoring Support (Medium)

For regulatory sources that update frequently, you can create a custom source class with **automated monitoring**.

### Benefits

✅ Automatically discover new documents
✅ Detect when documents are updated
✅ Trigger ETL pipeline on changes
✅ Track version history
✅ Schedule monitoring frequency

### Architecture

Monitoring sources implement the `MonitorableSource` mixin interface:

```python
class YourSource(DocumentSource, MonitorableSource):
    async def discover_documents(self) -> list[DiscoveredDocument]:
        """Scrape source website to find documents"""

    async def check_for_updates(self, known_document) -> ChangeDetectionResult:
        """Check if a document has changed"""

    def get_monitoring_schedule(self) -> str:
        """Return cron expression for monitoring"""

    def get_monitoring_priority(self) -> str:
        """Return 'high', 'medium', or 'low'"""
```

### Step 1: Create Your Source Class

Create a new file: `backend/green_gov_rag/etl/sources/your_source.py`

```python
"""Your source name with monitoring support."""

from __future__ import annotations

import hashlib
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

from green_gov_rag.etl.sources.base import (
    ChangeDetectionResult,
    DiscoveredDocument,
    DocumentSource,
    MonitorableSource,
    ValidationResult,
)


class YourSource(DocumentSource, MonitorableSource):
    """Your source with automated monitoring.

    Features:
    - Web scraping to discover new documents
    - Change detection via HTTP headers and content hashing
    - Configurable monitoring schedule
    - Priority-based processing
    """

    # Website to scrape
    SOURCE_URL = "https://example.gov.au/documents"

    def validate(self) -> ValidationResult:
        """Validate configuration."""
        errors = self._validate_required_fields()
        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def get_download_urls(self) -> list[str]:
        """Get download URLs from config or return empty list."""
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict:
        """Get document metadata."""
        metadata = {
            "title": self.config.get("title"),
            "jurisdiction": self.config.get("jurisdiction"),
            "category": self.config.get("category"),
            "topic": self.config.get("topic"),
        }
        # Add structured metadata if present
        metadata.update(self._extract_structured_metadata())
        return metadata

    def get_document_id(self, url: str) -> str:
        """Generate consistent document ID for delta indexing."""
        return self._generate_document_id(url)

    def get_destination_path(self, url: str, base_dir: str = "data/raw") -> str:
        """Get filesystem path for downloaded document."""
        return self._generate_destination_path(url, base_dir)

    async def discover_documents(self) -> list[DiscoveredDocument]:
        """Discover documents by scraping source website.

        Returns:
            List of discovered documents with metadata
        """
        discovered = []

        async with aiohttp.ClientSession() as session:
            async with session.get(self.SOURCE_URL) as response:
                if response.status != 200:
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find all PDF links
                pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))

                for link in pdf_links:
                    href = link.get('href', '')
                    title = link.get_text(strip=True)

                    # Make absolute URL
                    if not href.startswith('http'):
                        href = f"https://example.gov.au{href}"

                    discovered.append(
                        DiscoveredDocument(
                            url=href,
                            title=title,
                            metadata=self._extract_document_metadata(title),
                        )
                    )

        return discovered

    async def check_for_updates(
        self, known_document: dict
    ) -> ChangeDetectionResult:
        """Check if a known document has been updated.

        Strategy:
        1. Check Last-Modified header (fast, 90% confidence)
        2. Check ETag header (fast, 95% confidence)
        3. Fall back to content hash (slow, 100% confidence)

        Args:
            known_document: Dict with url, content_hash, last_modified

        Returns:
            ChangeDetectionResult indicating if document changed
        """
        url = known_document['url']

        async with aiohttp.ClientSession() as session:
            # Try HEAD request first (fast)
            try:
                async with session.head(url, allow_redirects=True) as response:
                    if response.status == 200:
                        # Check Last-Modified header
                        last_modified_str = response.headers.get('Last-Modified')
                        if last_modified_str:
                            # Parse date
                            from email.utils import parsedate_to_datetime
                            remote_date = parsedate_to_datetime(last_modified_str)

                            local_date = known_document.get('last_modified')
                            if local_date and remote_date > local_date:
                                return ChangeDetectionResult(
                                    has_changed=True,
                                    change_type='updated',
                                    confidence=0.9,
                                    details=f"Remote modified: {remote_date}",
                                )

                        # Check ETag header
                        etag = response.headers.get('ETag')
                        if etag and etag != known_document.get('etag'):
                            return ChangeDetectionResult(
                                has_changed=True,
                                change_type='updated',
                                confidence=0.95,
                                details=f"ETag changed: {etag}",
                            )
            except Exception:
                pass  # Fall back to content hash

            # Fall back to content hash (definitive but slow)
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        new_hash = hashlib.sha256(content).hexdigest()
                        old_hash = known_document.get('content_hash')

                        if new_hash != old_hash:
                            return ChangeDetectionResult(
                                has_changed=True,
                                change_type='updated',
                                old_hash=old_hash,
                                new_hash=new_hash,
                                confidence=1.0,
                                details="Content hash changed",
                            )
            except Exception as e:
                return ChangeDetectionResult(
                    has_changed=False,
                    change_type='error',
                    confidence=0.0,
                    details=f"Error checking: {str(e)}",
                )

        return ChangeDetectionResult(
            has_changed=False,
            change_type='unchanged',
            confidence=1.0,
        )

    def get_monitoring_schedule(self) -> str:
        """Get monitoring schedule (cron expression).

        Returns:
            Cron expression:
            - "0 2 * * *" - Daily at 2am
            - "0 */6 * * *" - Every 6 hours
            - "0 2 * * 1" - Weekly on Monday
            - "0 2 1 * *" - Monthly on 1st
        """
        return "0 2 * * *"  # Daily at 2am

    def get_monitoring_priority(self) -> str:
        """Get monitoring priority.

        Returns:
            - 'high' - Critical regulatory documents (NGER, ISSB)
            - 'medium' - Important policy documents
            - 'low' - Reference materials, historical docs
        """
        return "medium"

    def _extract_document_metadata(self, title: str) -> dict:
        """Extract metadata from document title.

        Parse title to identify frameworks, scopes, etc.
        """
        metadata = {}

        # Example: Look for emission scopes in title
        if 'Scope 1' in title:
            metadata['emission_scopes'] = ['scope_1']
        elif 'Scope 2' in title:
            metadata['emission_scopes'] = ['scope_2']
        elif 'Scope 3' in title:
            metadata['emission_scopes'] = ['scope_3']

        return metadata
```

### Step 2: Register Your Source (Optional)

If using a custom source type name, register it:

```python
# In green_gov_rag/etl/sources/__init__.py or registry.py
from green_gov_rag.etl.sources.registry import get_global_registry
from green_gov_rag.etl.sources.your_source import YourSource

registry = get_global_registry()
registry.register("your_source", YourSource)
```

### Step 3: Add Config Entry (Optional)

You can add a static config entry for fallback URLs:

```yaml
# backend/configs/documents_config.yml
- title: Your Source - Guidelines
  source_url: https://example.gov.au/documents
  source_type: your_source  # If custom type
  jurisdiction: federal
  category: environment
  topic: emissions_reporting
  region: Australia
  sovereign: true
  # download_urls are optional - monitoring will discover them
```

### Step 4: Add Unit Tests

Create `backend/tests/etl/sources/test_your_source.py`:

```python
"""Tests for YourSource."""

import pytest

from green_gov_rag.etl.sources.your_source import YourSource


@pytest.fixture
def source_config():
    """Sample configuration."""
    return {
        'title': 'Test Source',
        'jurisdiction': 'federal',
        'category': 'environment',
        'topic': 'test',
    }


def test_validation(source_config):
    """Test configuration validation."""
    source = YourSource(source_config)
    result = source.validate()

    assert result.is_valid
    assert len(result.errors) == 0


def test_get_metadata(source_config):
    """Test metadata extraction."""
    source = YourSource(source_config)
    metadata = source.get_metadata()

    assert metadata['title'] == 'Test Source'
    assert metadata['jurisdiction'] == 'federal'


def test_get_document_id(source_config):
    """Test document ID generation."""
    source = YourSource(source_config)
    doc_id = source.get_document_id("https://example.gov.au/doc.pdf")

    assert isinstance(doc_id, str)
    assert len(doc_id) > 0
    # ID should be consistent
    doc_id2 = source.get_document_id("https://example.gov.au/doc.pdf")
    assert doc_id == doc_id2


@pytest.mark.asyncio
async def test_discover_documents(source_config):
    """Test document discovery."""
    source = YourSource(source_config)

    # This will make real HTTP request - consider mocking
    discovered = await source.discover_documents()

    assert isinstance(discovered, list)
    # If source has documents, validate structure
    if len(discovered) > 0:
        doc = discovered[0]
        assert doc.url.startswith('http')
        assert len(doc.title) > 0


@pytest.mark.asyncio
async def test_check_for_updates(source_config):
    """Test change detection."""
    source = YourSource(source_config)

    known_doc = {
        'url': 'https://example.gov.au/doc.pdf',
        'content_hash': 'abc123',
        'last_modified': None,
    }

    result = await source.check_for_updates(known_doc)

    assert result.change_type in ['new', 'updated', 'unchanged', 'error']
    assert 0 <= result.confidence <= 1.0
```

### Step 5: Run Tests

```bash
cd backend

# Run your specific tests
pytest tests/etl/sources/test_your_source.py -v

# Run all source tests
pytest tests/etl/sources/ -v
```

### Step 6: Test Monitoring Service

```python
# Test script or Python REPL
import asyncio
from green_gov_rag.etl.sources.your_source import YourSource

async def test_monitoring():
    config = {
        'title': 'Test Source',
        'jurisdiction': 'federal',
        'category': 'environment',
        'topic': 'test',
    }
    source = YourSource(config)

    # Test discovery
    print("Discovering documents...")
    discovered = await source.discover_documents()
    print(f"Found {len(discovered)} documents:")
    for doc in discovered[:5]:  # Show first 5
        print(f"  - {doc.title}")
        print(f"    {doc.url}")

    # Test change detection
    if discovered:
        print("\nTesting change detection...")
        known_doc = {
            'url': discovered[0].url,
            'content_hash': 'test_hash',
        }
        result = await source.check_for_updates(known_doc)
        print(f"  Changed: {result.has_changed}")
        print(f"  Type: {result.change_type}")
        print(f"  Confidence: {result.confidence}")

asyncio.run(test_monitoring())
```

### Step 7: Submit Pull Request

Create a PR with:

- **Title:** `Add [Source Name] with monitoring support`
- **Description:**
    - What source you added
    - What documents it monitors
    - Monitoring schedule and priority
    - Testing evidence (logs/screenshots)
- **Files changed:**
    - `backend/green_gov_rag/etl/sources/your_source.py` (new)
    - `backend/tests/etl/sources/test_your_source.py` (new)
    - `backend/configs/documents_config.yml` (optional)
- **Labels:** `enhancement, monitoring`

---

## Reference Implementation

See **`backend/green_gov_rag/etl/sources/cer_emissions.py`** for a complete working example of a monitored source.

Key highlights:

- Scrapes Clean Energy Regulator website for NGER guidelines
- Multi-strategy change detection (Last-Modified, ETag, content hash)
- High priority monitoring (daily checks)
- Comprehensive error handling
- Full test coverage

---

## Metadata Reference

### ESG Metadata Fields

For emissions and ESG-related documents:

```yaml
esg_metadata:
  # Frameworks
  frameworks: [NGER, GHG_Protocol, ISSB, TCFD, SASB]
  measurement_standard: GHG_Protocol_Corporate_Standard

  # Emission Classification
  emission_scopes: [scope_1, scope_2, scope_3]
  greenhouse_gases: [CO2, CH4, N2O, SF6, HFCs, PFCs, NF3]

  # Methodology
  consolidation_method: operational_control  # or equity_share, financial_control
  methodology_type: calculation  # or measurement, estimation

  # NGER-Specific
  reportable_under_nger: true
  scope_3_reportable: false
  nger_threshold_tonnes: 25000

  # Regulatory
  regulator: Clean Energy Regulator
  regulation_type: guideline  # or standard, requirement

  # Activity Classification
  activity_types: [fuel_combustion, fugitive_emissions, industrial_process]
  facility_types: [coal_mine, gas_facility, manufacturing]
  industry_codes: [B0600]  # ANZSIC codes
```

### Spatial Metadata Fields

For geospatially-filtered documents:

```yaml
spatial_metadata:
  # Scope
  spatial_scope: federal  # or state, local
  state: NSW  # NSW, VIC, QLD, SA, WA, TAS, NT, ACT (or null for federal)

  # LGA Filtering
  lga_codes: [40070, 40071]  # ABS LGA codes
  lga_names: ["City of Adelaide", "Adelaide Hills"]
  applies_to_all_lgas: false
  applies_to_point: false

  # Optional: Specific coordinates
  latitude: -34.9285
  longitude: 138.6007
  buffer_km: 50
```

---

## Plugin Auto-Selection

The factory automatically selects the correct plugin based on your metadata:

1. **Has `esg_metadata`** → `EmissionsReportingSource`
2. **`jurisdiction == 'local'`** → `LocalGovernmentSource`
3. **`jurisdiction == 'state'`** → `StateLegislationSource`
4. **`jurisdiction == 'federal'` + `category == 'legislation'`** → `FederalLegislationSource`
5. **Default** → `GenericDocumentSource`

---

## Troubleshooting

### Validation Errors

- **Error:** "Missing required field: title"
- **Fix:** Ensure all required fields are present: title, jurisdiction, category, topic

- **Error:** "Invalid download URL"
- **Fix:** URLs must start with `http://` or `https://`

### Import Errors

- **Error:** "ModuleNotFoundError: No module named 'aiohttp'"
- **Fix:** Install dependencies: `pip install -e .[dev]`

### Web Scraping Issues

- **Error:** "Connection timeout" or "403 Forbidden"
- **Fix:**
    - Check if website requires authentication
    - Add User-Agent header to requests
    - Respect robots.txt
    - Consider rate limiting

### Monitoring Not Triggering

**Issue:** Documents not being discovered
**Debug:**
```python
# Test discovery directly
discovered = await source.discover_documents()
print(f"Found: {len(discovered)} documents")
for doc in discovered:
    print(f"  {doc.url}")
```

---

## Resources

### Documentation
- [Plugin Architecture](../developer-guide/architecture/plugin-system.md) - System design
- [Plugin API Reference](../reference/plugin-api.md) - Quick reference
- [Code Style Guide](code-style.md) - Coding standards
- [Testing Guide](testing.md) - How to write tests

### Code Examples
- `backend/green_gov_rag/etl/sources/base.py` - Base interfaces
- `backend/green_gov_rag/etl/sources/cer_emissions.py` - Monitoring example
- `backend/green_gov_rag/etl/sources/federal.py` - Federal legislation
- `backend/green_gov_rag/etl/sources/emissions.py` - Emissions reporting
- `backend/configs/documents_config.yml` - Configuration examples

### External Resources
- [Australian Legislation](https://www.legislation.gov.au/)
- [Clean Energy Regulator](https://cer.gov.au/)
- [ABS LGA Boundaries](https://www.abs.gov.au/statistics/mapping/geo-boundaries)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [aiohttp Documentation](https://docs.aiohttp.org/)

---

## Need Help?

- **Questions?** Open a [GitHub Discussion](https://github.com/sdp5/green-gov-rag/discussions)
- **Bug found?** Open a [GitHub Issue](https://github.com/sdp5/green-gov-rag/issues)
- **Quick questions?** Use the [Add Document Source template](https://github.com/sdp5/green-gov-rag/issues/new?template=add-document-source.md)

---

**Ready to contribute?** Pick an approach and submit your PR! 🚀
