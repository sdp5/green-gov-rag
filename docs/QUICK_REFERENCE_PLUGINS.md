# Document Source Plugins - Quick Reference

## 🚀 Quick Start

### Load All Documents
```python
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    print(source.get_metadata()["title"])
```

### Validate Configuration
```python
for source in sources:
    result = source.validate()
    if not result.is_valid:
        print(f"❌ {result.errors}")
```

### Filter by Type
```python
from green_gov_rag.etl.loader import get_document_sources_by_type

federal = get_document_sources_by_type('federal_legislation')
emissions = get_document_sources_by_type('emissions_reporting')
state = get_document_sources_by_type('state_legislation')
local = get_document_sources_by_type('local_government')
```

## 📋 Plugin Types

| Plugin | Config Pattern | Use Case |
|--------|----------------|----------|
| `FederalLegislationSource` | `jurisdiction: federal`<br>`category: legislation` | EPBC Act, NCC |
| `EmissionsReportingSource` | `topic: emissions_reporting`<br>or has `esg_metadata` | NGER, GHG Protocol, Scope 1/2/3 |
| `StateLegislationSource` | `jurisdiction: state` | NSW/VIC/QLD/SA/WA acts |
| `LocalGovernmentSource` | `jurisdiction: local` | City policies, LGA plans |
| `GenericDocumentSource` | Fallback | Unrecognized types |

## 🔧 Plugin API

### Required Methods
```python
class MySource(DocumentSource):
    def validate(self) -> ValidationResult:
        """Validate config - return ValidationResult"""

    def get_download_urls(self) -> list[str]:
        """Return list of URLs to download"""

    def get_metadata(self) -> dict:
        """Return metadata dict"""
```

### Helper Methods (Built-in)
```python
source._validate_required_fields()  # Check required fields
source._validate_urls()             # Validate URL format
source.get_source_type()            # Get type identifier
source.get_required_fields()        # List required fields
source.get_optional_fields()        # List optional fields
```

## 📝 Configuration Schema

### Minimal Config
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

### Emissions Document
```yaml
- title: NGER Guideline
  jurisdiction: federal
  topic: emissions_reporting
  esg_metadata:
    frameworks: [NGER, GHG_Protocol]
    emission_scopes: [scope_1]
    greenhouse_gases: [CO2, CH4, N2O]
    reportable_under_nger: true
```

### Local Government Document
```yaml
- title: City Guidelines
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

## 🎯 Specialized Methods

### EmissionsReportingSource
```python
source.get_emission_scopes()      # ['scope_1', 'scope_2']
source.get_scope_3_categories()   # ['purchased_goods_services', ...]
source.is_nger_reportable()       # True/False
source.get_esg_metadata()         # Full ESG metadata dict
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

## 🏗️ Create Custom Plugin

### 1. Create File: `my_plugin.py`
```python
from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult

class MyDocumentSource(DocumentSource):
    def validate(self) -> ValidationResult:
        errors = self._validate_required_fields()
        errors.extend(self._validate_urls())
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

### 2. Register in `factory.py`
```python
from my_plugin import MyDocumentSource

registry.register("my_document", MyDocumentSource)
```

### 3. Write Test: `test_my_plugin.py`
```python
def test_my_plugin():
    config = {"title": "Test", ...}
    source = MyDocumentSource(config)
    assert source.validate().is_valid
```

## 🧪 Testing

### Run All Tests
```bash
pytest tests/etl/sources/ -v
```

### Run Specific Plugin
```bash
pytest tests/etl/sources/test_federal.py -v
```

### Test Your Config
```bash
python -c "
from green_gov_rag.etl.loader import load_document_sources
sources = load_document_sources()
for s in sources:
    result = s.validate()
    if not result.is_valid:
        print(f'{s.config[\"title\"]}: {result.errors}')
"
```

## 📚 Common Patterns

### Load and Validate All
```python
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    validation = source.validate()
    if validation.is_valid:
        print(f"✅ {source.get_metadata()['title']}")
        for url in source.get_download_urls():
            print(f"   📥 {url}")
    else:
        print(f"❌ {source.get_metadata()['title']}")
        for error in validation.errors:
            print(f"   ⚠️  {error}")
```

### Filter Emissions by Scope
```python
from green_gov_rag.etl.loader import get_document_sources_by_type

emissions = get_document_sources_by_type('emissions_reporting')
scope_1 = [s for s in emissions if 'scope_1' in s.get_emission_scopes()]
scope_3 = [s for s in emissions if 'scope_3' in s.get_emission_scopes()]

print(f"Scope 1 docs: {len(scope_1)}")
print(f"Scope 3 docs: {len(scope_3)}")
```

### Filter by State/LGA
```python
sources = load_document_sources()

# All SA documents
sa_docs = [s for s in sources
           if s.get_metadata().get('spatial_metadata', {}).get('state') == 'SA']

# Federal + SA state + SA local
applicable_to_sa = [s for s in sources
                    if s.get_metadata().get('jurisdiction') == 'federal'
                    or s.get_metadata().get('spatial_metadata', {}).get('state') == 'SA']
```

### Get All URLs for Download
```python
all_urls = []
for source in load_document_sources():
    all_urls.extend(source.get_download_urls())

print(f"Total URLs: {len(all_urls)}")
```

## 🐛 Troubleshooting

### Plugin Not Auto-Detected
Update `factory.py` `_infer_source_type()`:
```python
if config.get("topic") == "my_topic":
    return "my_document"
```

### Validation Always Fails
Check required fields:
```python
def get_required_fields(self) -> list[str]:
    return ["title", "jurisdiction", "category"]
```

### Import Errors
Export in `__init__.py`:
```python
from .my_plugin import MyDocumentSource
__all__ = [..., "MyDocumentSource"]
```

## 📖 Resources

- **Full Guide**: `docs/CONTRIBUTING_DOCUMENT_SOURCES.md`
- **Architecture**: `docs/PLUGIN_ARCHITECTURE_SUMMARY.md`
- **Module README**: `green_gov_rag/etl/sources/README.md`
- **Demo Script**: `examples/document_sources_demo.py`
- **Issue Template**: `.github/ISSUE_TEMPLATE/add-document-source.md`

## 💡 Tips

1. **Start simple** - Add config first, create plugin later if needed
2. **Use existing plugins** - Most documents fit federal/state/local/emissions
3. **Validate early** - Run validation before submitting PR
4. **Check examples** - Look at `configs/documents_config.yml` for patterns
5. **Ask questions** - Open GitHub issue if stuck!
