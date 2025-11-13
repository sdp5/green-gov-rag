# Plugin Quick Reference

## Quick Start

### Load All Documents

```python
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    print(source.get_metadata()["title"])
```

### Validate

```python
for source in sources:
    result = source.validate()
    if not result.is_valid:
        print(f"Errors: {result.errors}")
```

### Filter by Type

```python
from green_gov_rag.etl.loader import get_document_sources_by_type

federal = get_document_sources_by_type('federal_legislation')
emissions = get_document_sources_by_type('emissions_reporting')
```

## Plugin Types

| Plugin | Triggers | Use Case |
|--------|----------|----------|
| `FederalLegislationSource` | `jurisdiction: federal`<br>`category: legislation` | EPBC Act, NCC |
| `EmissionsReportingSource` | `topic: emissions_reporting`<br>or has `esg_metadata` | NGER, GHG Protocol |
| `StateLegislationSource` | `jurisdiction: state` | State acts |
| `LocalGovernmentSource` | `jurisdiction: local` | LGA policies |
| `GenericDocumentSource` | Fallback | Unrecognized types |

## Plugin API

### Required Methods

```python
class MySource(DocumentSource):
    def validate(self) -> ValidationResult:
        """Validate config"""

    def get_download_urls(self) -> list[str]:
        """Return download URLs"""

    def get_metadata(self) -> dict:
        """Return metadata"""
```

### Helper Methods

```python
source._validate_required_fields()  # Check required
source._validate_urls()             # Validate URLs
source.get_source_type()            # Type identifier
```

## Configuration

### Minimal

```yaml
- title: Document Title
  jurisdiction: federal  # or state, local
  category: legislation
  topic: environment
```

### With Downloads

```yaml
- title: Document Title
  source_url: https://example.gov.au/
  download_urls:
    - https://example.gov.au/doc.pdf
  jurisdiction: federal
  category: legislation
  topic: environment
```

### Emissions

```yaml
- title: NGER Guideline
  jurisdiction: federal
  topic: emissions_reporting
  esg_metadata:
    frameworks: [NGER, GHG_Protocol]
    emission_scopes: [scope_1]
    greenhouse_gases: [CO2, CH4, N2O]
```

### Local Government

```yaml
- title: City Guidelines
  jurisdiction: local
  category: development_plan
  spatial_metadata:
    spatial_scope: local
    state: SA
    lga_codes: [40070]
    lga_names: [City of Adelaide]
```

## Specialized Methods

### EmissionsReportingSource

```python
source.get_emission_scopes()      # ['scope_1', 'scope_2']
source.get_scope_3_categories()   # ['purchased_goods_services', ...]
source.is_nger_reportable()       # True/False
source.get_esg_metadata()         # Full ESG dict
```

### LocalGovernmentSource

```python
source.get_lga_codes()      # [40070, 40280]
source.get_lga_names()      # ['City of Adelaide']
source.get_state()          # 'SA'
source.applies_to_point()   # True/False
```

### StateLegislationSource

```python
source.get_state()          # 'NSW', 'VIC', etc.
```

## Create Custom Plugin

### 1. Create File

```python
from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult

class MyDocumentSource(DocumentSource):
    def validate(self) -> ValidationResult:
        errors = self._validate_required_fields()
        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def get_download_urls(self) -> list[str]:
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict:
        return {"title": self.config.get("title")}

    def get_source_type(self) -> str:
        return "my_document"
```

### 2. Register

```python
# In factory.py
registry.register("my_document", MyDocumentSource)
```

### 3. Test

```python
def test_my_plugin():
    config = {"title": "Test", ...}
    source = MyDocumentSource(config)
    assert source.validate().is_valid
```

## Testing

```bash
# All tests
pytest tests/etl/sources/ -v

# Specific plugin
pytest tests/etl/sources/test_federal.py -v

# Test your config
python -c "
from green_gov_rag.etl.loader import load_document_sources
for s in load_document_sources():
    result = s.validate()
    if not result.is_valid:
        print(f'{s.config[\"title\"]}: {result.errors}')
"
```

## Common Patterns

### Load and Validate

```python
sources = load_document_sources()
for source in sources:
    if source.validate().is_valid:
        print(f"✅ {source.get_metadata()['title']}")
        for url in source.get_download_urls():
            print(f"   {url}")
```

### Filter Emissions by Scope

```python
emissions = get_document_sources_by_type('emissions_reporting')
scope_1 = [s for s in emissions if 'scope_1' in s.get_emission_scopes()]
```

### Filter by State/LGA

```python
# All SA documents
sa_docs = [s for s in sources
           if s.get_metadata().get('spatial_metadata', {}).get('state') == 'SA']
```

### Get All URLs

```python
all_urls = []
for source in load_document_sources():
    all_urls.extend(source.get_download_urls())
```

## Troubleshooting

**Plugin not detected:** Update `_infer_source_type()` in `factory.py`

**Validation fails:** Check required fields in `get_required_fields()`

**Import errors:** Export in `__init__.py`

## Resources

- [Full Guide](./CONTRIBUTING_DOCUMENT_SOURCES.md)
- [Architecture](./PLUGIN_ARCHITECTURE_SUMMARY.md)
- [Data Sources](./DATA.md)

## See Also

- [Contributing Guide](./CONTRIBUTING_DOCUMENT_SOURCES.md) - Detailed plugin creation
- [Plugin Architecture](./PLUGIN_ARCHITECTURE_SUMMARY.md) - System design
- [Data Sources](./DATA.md) - Available documents
