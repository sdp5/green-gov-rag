# Document Source Plugins

This module provides a **plugin-based architecture** for handling different types of government documents in the ETL pipeline.

## Overview

The plugin system enables easy extension of document types without modifying core code. Each document type is represented by a `DocumentSource` plugin that handles validation, metadata extraction, and type-specific processing.

## Architecture

```
DocumentSource (ABC)
    │
    ├── FederalLegislationSource     - Federal laws and regulations
    ├── EmissionsReportingSource     - ESG/NGER/GHG Protocol documents
    ├── StateLegislationSource       - State-level legislation
    ├── LocalGovernmentSource        - LGA-specific policies
    └── GenericDocumentSource        - Fallback for unrecognized types
```

## Quick Start

### Load All Sources

```python
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    print(source.get_metadata())
```

### Filter by Type

```python
from green_gov_rag.etl.loader import get_document_sources_by_type

federal_sources = get_document_sources_by_type('federal_legislation')
emissions_sources = get_document_sources_by_type('emissions_reporting')
```

### Validate Configuration

```python
for source in sources:
    validation = source.validate()
    if not validation.is_valid:
        print(f"Errors: {validation.errors}")
```

## Plugin API

Every `DocumentSource` plugin must implement:

### Required Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `validate()` | `ValidationResult` | Validate configuration |
| `get_download_urls()` | `list[str]` | Get URLs to download |
| `get_metadata()` | `dict` | Get document metadata |

### Optional Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_source_type()` | `str` | Plugin type identifier |
| `get_required_fields()` | `list[str]` | Required config fields |
| `get_optional_fields()` | `list[str]` | Optional config fields |

## Built-in Plugins

### FederalLegislationSource

Handles Australian federal legislation and regulations.

**Example:**
```yaml
title: EPBC Act
jurisdiction: federal
category: legislation
topic: biodiversity
```

**Specializations:**
- Validates `jurisdiction == 'federal'`
- Checks `spatial_scope == 'federal'`
- Warns on unusual categories

### EmissionsReportingSource

Handles emissions reporting frameworks (NGER, GHG Protocol, ISSB).

**Example:**
```yaml
title: NGER Scope 1 Guideline
jurisdiction: federal
topic: emissions_reporting
esg_metadata:
  frameworks: [NGER]
  emission_scopes: [scope_1]
```

**Specializations:**
- Validates ESG metadata structure
- Provides `get_emission_scopes()`
- Provides `get_scope_3_categories()`
- Provides `is_nger_reportable()`

### StateLegislationSource

Handles state-level legislation (NSW, VIC, QLD, SA, WA, TAS, NT, ACT).

**Example:**
```yaml
title: NSW EPA Act
jurisdiction: state
category: legislation
spatial_metadata:
  state: NSW
  spatial_scope: state
```

**Specializations:**
- Validates state codes
- Validates `jurisdiction == 'state'`
- Provides `get_state()`

### LocalGovernmentSource

Handles LGA-specific documents and policies.

**Example:**
```yaml
title: City of Adelaide Guidelines
jurisdiction: local
category: development_plan
spatial_metadata:
  spatial_scope: local
  state: SA
  lga_codes: [40070]
  lga_names: [City of Adelaide]
```

**Specializations:**
- Requires `spatial_metadata`
- Validates LGA codes and names
- Provides `get_lga_codes()`
- Provides `get_lga_names()`
- Provides `applies_to_point()`

## Creating Custom Plugins

### Step 1: Define Plugin Class

```python
# green_gov_rag/etl/sources/my_plugin.py
from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult

class MyDocumentSource(DocumentSource):
    def validate(self) -> ValidationResult:
        errors = self._validate_required_fields()
        errors.extend(self._validate_urls())
        # Add custom validation
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

### Step 2: Register Plugin

```python
# green_gov_rag/etl/sources/factory.py
from green_gov_rag.etl.sources.my_plugin import MyDocumentSource

def _create_default_registry(self):
    registry = DocumentSourceRegistry()
    # ... existing registrations ...
    registry.register("my_document", MyDocumentSource)
    return registry
```

### Step 3: Write Tests

```python
# tests/etl/sources/test_my_plugin.py
def test_my_plugin():
    config = {"title": "Test", ...}
    source = MyDocumentSource(config)
    assert source.validate().is_valid
```

## Factory Pattern

The `DocumentSourceFactory` automatically creates the correct plugin based on configuration:

```python
from green_gov_rag.etl.sources.factory import DocumentSourceFactory

factory = DocumentSourceFactory()
source = factory.create_source(config_dict)
# Returns appropriate plugin instance
```

### Type Inference Rules

The factory infers source type from config:

1. **Has `esg_metadata`** → `EmissionsReportingSource`
2. **`jurisdiction == 'local'`** → `LocalGovernmentSource`
3. **`jurisdiction == 'state'`** → `StateLegislationSource`
4. **`jurisdiction == 'federal'` + `category == 'legislation'`** → `FederalLegislationSource`
5. **Default** → `GenericDocumentSource`

## Registry Pattern

The `DocumentSourceRegistry` manages plugin registration and discovery:

```python
from green_gov_rag.etl.sources.registry import get_global_registry

registry = get_global_registry()
registry.register("custom_type", CustomSource)

# Load sources filtered by type
sources = registry.load_from_config("config.yml", source_type="custom_type")
```

## Validation

### ValidationResult

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
```

**Usage:**
```python
result = source.validate()
if not result.is_valid:
    print(f"Errors: {result.errors}")
if result.warnings:
    print(f"Warnings: {result.warnings}")
```

## Testing

Run plugin tests:

```bash
# All source tests
pytest tests/etl/sources/ -v

# Specific plugin
pytest tests/etl/sources/test_federal.py -v
```

## Files

```
green_gov_rag/etl/sources/
├── __init__.py              # Module exports
├── base.py                  # DocumentSource ABC, ValidationResult
├── registry.py              # Plugin registry
├── factory.py               # Factory + GenericDocumentSource
├── federal.py               # FederalLegislationSource
├── emissions.py             # EmissionsReportingSource
├── state.py                 # StateLegislationSource
├── local_government.py      # LocalGovernmentSource
└── README.md               # This file
```

## Contributing

See [CONTRIBUTING_DOCUMENT_SOURCES.md](../../../docs/CONTRIBUTING_DOCUMENT_SOURCES.md) for detailed contribution guide.

**Good first issues:**
- Add new document to `configs/documents_config.yml`
- Create plugin for new document category
- Improve validation logic
- Add spatial filtering helpers

## Examples

Run the demo:

```bash
python examples/document_sources_demo.py
```

See example code in `examples/document_sources_demo.py` for comprehensive usage patterns.
