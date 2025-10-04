# Contributing Document Sources

This guide explains how to add new document sources to the green-gov-rag project using the plugin architecture.

## Overview

The project uses a **plugin-based architecture** for document sources, making it easy to add support for new document types without modifying core code.

Each document type is represented by a **DocumentSource plugin** that handles:
- ✅ Configuration validation
- ✅ Download URL extraction
- ✅ Metadata processing
- ✅ Type-specific business logic

## Quick Start (5 minutes)

### 1. Choose Your Document Type

Identify which plugin type best fits your document:

| Plugin Type | Use Case | Example |
|-------------|----------|---------|
| `FederalLegislationSource` | Australian federal laws & regulations | EPBC Act, NCC |
| `EmissionsReportingSource` | ESG/NGER/GHG Protocol documents | Scope 1/2/3 guidance |
| `StateLegislationSource` | State-level legislation | NSW EPA Act, VIC Planning |
| `LocalGovernmentSource` | LGA-specific policies | City of Adelaide plans |

### 2. Add Configuration Entry

Add your document to `configs/documents_config.yml`:

```yaml
- title: Your Document Title
  source_url: https://example.gov.au/
  download_urls:
    - https://example.gov.au/document.pdf
  jurisdiction: federal  # or 'state', 'local'
  category: legislation  # e.g., 'legislation', 'policy', 'guideline'
  topic: your_topic
  region: Australia
  sovereign: true
```

### 3. Test It

```bash
# Load and validate
python -c "
from green_gov_rag.etl.loader import load_document_sources
sources = load_document_sources()
for s in sources:
    if 'Your Document' in s.config['title']:
        print(s.validate())
        print(s.get_metadata())
"
```

That's it! The factory automatically creates the correct plugin based on your config.

## Adding a New Plugin Type

Want to support a new document category? Create a custom plugin.

### Step 1: Create Plugin File

Create `green_gov_rag/etl/sources/your_source.py`:

```python
from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult

class YourDocumentSource(DocumentSource):
    """Your document type description."""

    def validate(self) -> ValidationResult:
        """Validate configuration."""
        errors = self._validate_required_fields()
        errors.extend(self._validate_urls())

        # Add custom validation
        if self.config.get("custom_field") is None:
            errors.append("Missing custom_field")

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def get_download_urls(self) -> list[str]:
        """Get download URLs."""
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict:
        """Get metadata."""
        return {
            "title": self.config.get("title"),
            "jurisdiction": self.config.get("jurisdiction"),
            # Add custom metadata
        }

    def get_source_type(self) -> str:
        """Return 'your_source'."""
        return "your_source"
```

### Step 2: Register Plugin

Update `green_gov_rag/etl/sources/factory.py`:

```python
from green_gov_rag.etl.sources.your_source import YourDocumentSource

def _create_default_registry(self):
    registry = DocumentSourceRegistry()
    # ... existing registrations ...
    registry.register("your_source", YourDocumentSource)
    return registry
```

### Step 3: Write Tests

Create `tests/etl/sources/test_your_source.py`:

```python
from green_gov_rag.etl.sources.your_source import YourDocumentSource

class TestYourDocumentSource:
    def test_validate_success(self):
        config = {
            "title": "Test",
            "jurisdiction": "federal",
            "category": "test",
            "topic": "test",
        }
        source = YourDocumentSource(config)
        result = source.validate()
        assert result.is_valid is True

    def test_get_metadata(self):
        config = {"title": "Test Document"}
        source = YourDocumentSource(config)
        metadata = source.get_metadata()
        assert metadata["title"] == "Test Document"
```

### Step 4: Run Tests

```bash
pytest tests/etl/sources/test_your_source.py -v
```

## Configuration Schema

### Required Fields

All documents must have:
- `title`: Document title
- `jurisdiction`: `federal`, `state`, or `local`
- `category`: Document category (e.g., `legislation`, `guideline`)
- `topic`: Document topic (e.g., `biodiversity`, `emissions_reporting`)

### Optional Fields

- `source_url`: Primary source website
- `download_urls`: List of PDF/HTML URLs to download
- `region`: Geographic region
- `sovereign`: Boolean (default: `true`)
- `esg_metadata`: ESG/emissions-specific metadata
- `spatial_metadata`: Geographic/LGA metadata

### Example: Federal Legislation

```yaml
- title: EPBC Act
  source_url: https://www.legislation.gov.au/Series/C2004A00485
  download_urls:
    - https://www.legislation.gov.au/.../pdf/1
  jurisdiction: federal
  category: legislation
  topic: biodiversity
  region: Australia
  sovereign: true
  spatial_metadata:
    spatial_scope: federal
    applies_to_all_lgas: true
```

### Example: Emissions Reporting

```yaml
- title: NGER Scope 1 Guideline
  source_url: https://cer.gov.au/
  download_urls:
    - https://cer.gov.au/document/...
  jurisdiction: federal
  category: environment
  topic: emissions_reporting
  esg_metadata:
    frameworks: [NGER, GHG_Protocol]
    emission_scopes: [scope_1]
    greenhouse_gases: [CO2, CH4, N2O]
    reportable_under_nger: true
```

### Example: Local Government

```yaml
- title: City of Adelaide Development Guidelines
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
```

## API Usage

### Loading Sources

```python
from green_gov_rag.etl.loader import load_document_sources

# Load all sources
sources = load_document_sources()

# Iterate and process
for source in sources:
    # Validate configuration
    validation = source.validate()
    if not validation.is_valid:
        print(f"Errors: {validation.errors}")
        continue

    # Get metadata
    metadata = source.get_metadata()
    print(f"Title: {metadata['title']}")

    # Get download URLs
    urls = source.get_download_urls()
    for url in urls:
        print(f"Download: {url}")
```

### Filtering by Type

```python
from green_gov_rag.etl.loader import get_document_sources_by_type

# Get only federal legislation
federal_sources = get_document_sources_by_type('federal_legislation')

# Get only emissions reporting
emissions_sources = get_document_sources_by_type('emissions_reporting')
```

### Filtering by Jurisdiction

```python
from green_gov_rag.etl.loader import get_document_sources_by_jurisdiction

# Get all federal documents
federal = get_document_sources_by_jurisdiction('federal')

# Get all local government documents
local = get_document_sources_by_jurisdiction('local')
```

## Architecture Diagram

```
configs/documents_config.yml
         │
         ├─→ DocumentSourceFactory
         │          │
         │          ├─→ FederalLegislationSource
         │          ├─→ EmissionsReportingSource
         │          ├─→ StateLegislationSource
         │          └─→ LocalGovernmentSource
         │
         └─→ loader.py → load_document_sources()
                              │
                              └─→ [List of DocumentSource plugins]
```

## Best Practices

1. **Validation First**: Always validate config before processing
2. **Use Type Hints**: All methods should have proper type annotations
3. **Write Tests**: Minimum 2-3 tests per plugin
4. **Document Examples**: Include config examples in docstrings
5. **Keep it Simple**: Plugins should be ~50-150 lines max

## Common Issues

### Issue: Source type not inferred correctly

**Solution**: Update `_infer_source_type()` in `factory.py` with your logic:

```python
def _infer_source_type(self, config: dict) -> str:
    topic = config.get("topic", "").lower()

    # Add your custom inference
    if topic == "your_topic":
        return "your_source"

    # ... existing logic ...
```

### Issue: Validation always fails

**Solution**: Check required fields match your config:

```python
def get_required_fields(self) -> list[str]:
    return ["title", "jurisdiction", "category", "topic"]
```

### Issue: Tests fail with import errors

**Solution**: Ensure `__init__.py` exports your plugin:

```python
# green_gov_rag/etl/sources/__init__.py
from green_gov_rag.etl.sources.your_source import YourDocumentSource

__all__ = [..., "YourDocumentSource"]
```

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: File a GitHub Issue
- **Examples**: Check existing plugins in `green_gov_rag/etl/sources/`

---

**Ready to contribute?** Pick a "good first issue" or add a document from the backlog!
