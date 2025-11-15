# Plugin Architecture Summary

Plugin-based architecture for extensible document source management.

## Overview

System uses **Strategy**, **Factory**, and **Registry** design patterns for maintainable, contributor-friendly architecture.

## Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Base Interface | `base.py` | Abstract `DocumentSource` class + validation |
| Registry | `registry.py` | Plugin registration and discovery |
| Factory | `factory.py` | Auto-creates plugins from config |
| Plugins | `federal.py`, `emissions.py`, etc. | Document type implementations |

## Built-in Plugins

| Plugin | File | Use Case |
|--------|------|----------|
| `FederalLegislationSource` | `federal.py` | Federal laws & regulations |
| `EmissionsReportingSource` | `emissions.py` | ESG/NGER/GHG Protocol |
| `StateLegislationSource` | `state.py` | State-level legislation |
| `LocalGovernmentSource` | `local_government.py` | LGA-specific policies |
| `GenericDocumentSource` | `factory.py` | Fallback for unrecognized types |

## Design Patterns

### Strategy Pattern

Each document type implements `DocumentSource` interface:

```python
class DocumentSource(ABC):
    def validate() -> ValidationResult
    def get_download_urls() -> list[str]
    def get_metadata() -> dict
```

### Factory Pattern

Factory creates appropriate plugin from config:

```python
factory = DocumentSourceFactory()
source = factory.create_source(config)  # Auto-detects type
```

### Registry Pattern

Registry manages plugin discovery:

```python
registry.register("federal_legislation", FederalLegislationSource)
sources = registry.load_from_config("config.yml")
```

## Architecture Flow

```
configs/documents_config.yml
         ↓
DocumentSourceFactory
         ↓
    ├─ FederalLegislationSource
    ├─ EmissionsReportingSource
    ├─ StateLegislationSource
    └─ LocalGovernmentSource
         ↓
loader.py → load_document_sources()
         ↓
[List of DocumentSource plugins]
```

## Key Features

### Easy Contribution

**Before:**
```python
# Hard-coded logic
if doc["jurisdiction"] == "federal":
    # Process federal...
```

**After:**
```yaml
# Just add YAML - plugin auto-selected!
- title: New Document
  jurisdiction: federal
```

### Type Safety

```python
sources: list[DocumentSource] = load_document_sources()
validation: ValidationResult = source.validate()
metadata: dict = source.get_metadata()
```

### Built-in Validation

```python
validation = source.validate()
if not validation.is_valid:
    print(f"Errors: {validation.errors}")
    print(f"Warnings: {validation.warnings}")
```

### Specialized Methods

```python
# Emissions reporting
emissions_source.get_emission_scopes()
emissions_source.is_nger_reportable()

# Local government
local_source.get_lga_codes()
local_source.get_lga_names()

# State legislation
state_source.get_state()
```

## File Structure

```
green_gov_rag/etl/sources/
├── __init__.py
├── base.py                  # DocumentSource ABC
├── registry.py              # Plugin registry
├── factory.py               # Factory + Generic
├── federal.py               # Federal legislation
├── emissions.py             # Emissions reporting
├── state.py                 # State legislation
├── local_government.py      # Local government
└── README.md

tests/etl/sources/
├── test_base.py            # Base tests (14)
├── test_factory.py         # Factory tests (15)
└── test_plugins.py         # Plugin tests (16)
```

## API Usage

### Load All Sources

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

## Testing

```bash
# Run all tests
pytest tests/etl/sources/ -v

# 45 tests, 100% coverage
```

## Benefits

### For Contributors
- Clear plugin interface (~50 lines)
- Template-based development
- Isolated testing
- GitHub issue templates

### For Maintainers
- Separation of concerns
- Easy PR review (small changes)
- Type-safe with IDE autocomplete
- Comprehensive test coverage

### For Users
- Better validation with error messages
- Type-specific helper methods
- Filtering and querying
- Backward compatible

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code added | ~1200 |
| Plugins implemented | 4 + 1 generic |
| Tests added | 45 |
| Test coverage | 100% |
| Backward compatibility | Maintained |
| Breaking changes | None |

## Migration

### Backward Compatible

```python
# Old API - still works
from green_gov_rag.etl.loader import load_documents_config
docs = load_documents_config()  # Returns list[dict]

# New API - recommended
from green_gov_rag.etl.loader import load_document_sources
sources = load_document_sources()  # Returns list[DocumentSource]
```

## See Also

- [Contributing Guide](./CONTRIBUTING_DOCUMENT_SOURCES.md) - Add new sources
- [Quick Reference](./QUICK_REFERENCE_PLUGINS.md) - API cheat sheet
- [Data Sources](./DATA.md) - Available documents
