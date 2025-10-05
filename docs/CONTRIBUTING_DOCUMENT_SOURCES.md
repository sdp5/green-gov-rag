# Contributing Document Sources

Add new document sources using the plugin architecture.

## Quick Start (5 minutes)

### 1. Choose Plugin Type

| Plugin | Use Case | Example |
|--------|----------|---------|
| `FederalLegislationSource` | Federal laws | EPBC Act, NCC |
| `EmissionsReportingSource` | ESG/NGER documents | Scope 1/2/3 guidance |
| `StateLegislationSource` | State legislation | NSW EPA Act |
| `LocalGovernmentSource` | LGA policies | City plans |

### 2. Add Config Entry

Edit `configs/documents_config.yml`:

```yaml
- title: Your Document Title
  source_url: https://example.gov.au/
  download_urls:
    - https://example.gov.au/document.pdf
  jurisdiction: federal  # or state, local
  category: legislation
  topic: your_topic
  region: Australia
  sovereign: true
```

### 3. Test

```bash
python -c "
from green_gov_rag.etl.loader import load_document_sources
sources = load_document_sources()
for s in sources:
    if 'Your Document' in s.config['title']:
        print(s.validate())
        print(s.get_metadata())
"
```

Done! The factory auto-creates the correct plugin.

## Create Custom Plugin

### 1. Create Plugin File

`green_gov_rag/etl/sources/your_source.py`:

```python
from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult

class YourDocumentSource(DocumentSource):
    """Your document type description."""

    def validate(self) -> ValidationResult:
        errors = self._validate_required_fields()
        errors.extend(self._validate_urls())
        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def get_download_urls(self) -> list[str]:
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict:
        return {
            "title": self.config.get("title"),
            "jurisdiction": self.config.get("jurisdiction"),
        }

    def get_source_type(self) -> str:
        return "your_source"
```

### 2. Register Plugin

Update `green_gov_rag/etl/sources/factory.py`:

```python
from green_gov_rag.etl.sources.your_source import YourDocumentSource

def _create_default_registry(self):
    registry = DocumentSourceRegistry()
    # ... existing ...
    registry.register("your_source", YourDocumentSource)
    return registry
```

### 3. Write Tests

`tests/etl/sources/test_your_source.py`:

```python
from green_gov_rag.etl.sources.your_source import YourDocumentSource

def test_validate_success():
    config = {
        "title": "Test",
        "jurisdiction": "federal",
        "category": "test",
        "topic": "test",
    }
    source = YourDocumentSource(config)
    assert source.validate().is_valid

def test_get_metadata():
    config = {"title": "Test Document"}
    source = YourDocumentSource(config)
    assert source.get_metadata()["title"] == "Test Document"
```

### 4. Run Tests

```bash
pytest tests/etl/sources/test_your_source.py -v
```

## Configuration Schema

### Required Fields

```yaml
title: Document title
jurisdiction: federal/state/local
category: legislation/policy/guideline
topic: biodiversity/emissions_reporting/zoning
```

### Optional Fields

```yaml
source_url: Primary source website
download_urls: [List of PDF/HTML URLs]
region: Geographic region
sovereign: true/false
esg_metadata: ESG/emissions metadata
spatial_metadata: Geographic/LGA metadata
```

### Examples

**Federal Legislation:**
```yaml
- title: EPBC Act
  source_url: https://www.legislation.gov.au/Series/C2004A00485
  download_urls:
    - https://www.legislation.gov.au/.../pdf/1
  jurisdiction: federal
  category: legislation
  topic: biodiversity
  spatial_metadata:
    spatial_scope: federal
    applies_to_all_lgas: true
```

**Emissions Reporting:**
```yaml
- title: NGER Scope 1 Guideline
  source_url: https://cer.gov.au/
  jurisdiction: federal
  topic: emissions_reporting
  esg_metadata:
    frameworks: [NGER, GHG_Protocol]
    emission_scopes: [scope_1]
    greenhouse_gases: [CO2, CH4, N2O]
```

**Local Government:**
```yaml
- title: City of Adelaide Guidelines
  jurisdiction: local
  category: development_plan
  topic: zoning
  spatial_metadata:
    spatial_scope: local
    state: SA
    lga_codes: [40070]
    lga_names: [City of Adelaide]
    applies_to_all_lgas: false
```

## API Usage

### Load Sources

```python
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    validation = source.validate()
    if validation.is_valid:
        metadata = source.get_metadata()
        urls = source.get_download_urls()
```

### Filter by Type

```python
from green_gov_rag.etl.loader import get_document_sources_by_type

federal = get_document_sources_by_type('federal_legislation')
emissions = get_document_sources_by_type('emissions_reporting')
```

### Filter by Jurisdiction

```python
from green_gov_rag.etl.loader import get_document_sources_by_jurisdiction

federal_docs = get_document_sources_by_jurisdiction('federal')
local_docs = get_document_sources_by_jurisdiction('local')
```

## Best Practices

1. **Validate first** - Always validate config before processing
2. **Use type hints** - All methods need type annotations
3. **Write tests** - Minimum 2-3 tests per plugin
4. **Document examples** - Include config examples in docstrings
5. **Keep simple** - Plugins should be ~50-150 lines

## Troubleshooting

### Plugin not auto-detected

Update `_infer_source_type()` in `factory.py`:

```python
def _infer_source_type(self, config: dict) -> str:
    if config.get("topic") == "your_topic":
        return "your_source"
```

### Validation always fails

Check required fields match your config:

```python
def get_required_fields(self) -> list[str]:
    return ["title", "jurisdiction", "category", "topic"]
```

### Import errors

Export in `__init__.py`:

```python
from green_gov_rag.etl.sources.your_source import YourDocumentSource
__all__ = [..., "YourDocumentSource"]
```

## See Also

- [Plugin Architecture](./PLUGIN_ARCHITECTURE_SUMMARY.md) - System design
- [Quick Reference](./QUICK_REFERENCE_PLUGINS.md) - API cheat sheet
- [Data Sources](./DATA.md) - Available data sources
