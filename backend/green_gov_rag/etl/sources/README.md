# Document Source Plugins

Plugin-based architecture for handling different government document types in the ETL pipeline.

## Quick Start

```python
# Load all sources
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    if source.validate().is_valid:
        print(source.get_metadata())

# Filter by type
federal_sources = get_document_sources_by_type('federal_legislation')
```

## Built-in Plugins

### FederalLegislationSource
Australian federal legislation and regulations.

```yaml
title: EPBC Act
jurisdiction: federal
category: legislation
topic: biodiversity
```

### EmissionsReportingSource
Emissions reporting frameworks (NGER, GHG Protocol, ISSB).

```yaml
title: NGER Scope 1 Guideline
jurisdiction: federal
topic: emissions_reporting
esg_metadata:
  frameworks: [NGER]
  emission_scopes: [scope_1]
```

### StateLegislationSource
State-level legislation (NSW, VIC, QLD, SA, WA, TAS, NT, ACT).

```yaml
title: NSW EPA Act
jurisdiction: state
category: legislation
spatial_metadata:
  state: NSW
```

### LocalGovernmentSource
LGA-specific documents and policies.

```yaml
title: City of Adelaide Guidelines
jurisdiction: local
spatial_metadata:
  state: SA
  lga_codes: [40070]
  lga_names: [City of Adelaide]
```

## Creating Custom Plugins

### 1. Define Plugin Class

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

### 2. Register Plugin

```python
from green_gov_rag.etl.sources.registry import get_global_registry

registry = get_global_registry()
registry.register("my_document", MyDocumentSource)
```

### 3. Add to Config

```yaml
# configs/documents_config.yml
- title: My Document
  source_type: my_document
  download_urls: [...]
```

## Factory Pattern

Auto-creates correct plugin from config:

```python
from green_gov_rag.etl.sources.factory import DocumentSourceFactory

factory = DocumentSourceFactory()
source = factory.create_source(config_dict)
```

**Type Inference Rules:**
1. Has `esg_metadata` → `EmissionsReportingSource`
2. `jurisdiction == 'local'` → `LocalGovernmentSource`
3. `jurisdiction == 'state'` → `StateLegislationSource`
4. `jurisdiction == 'federal'` + `category == 'legislation'` → `FederalLegislationSource`
5. Default → `GenericDocumentSource`

## Validation

```python
result = source.validate()
if not result.is_valid:
    print(f"Errors: {result.errors}")
if result.warnings:
    print(f"Warnings: {result.warnings}")
```

## Testing

```bash
# All plugin tests
pytest tests/etl/sources/ -v

# Specific plugin
pytest tests/etl/sources/test_federal.py -v
```

## Structure

```
etl/sources/
├── base.py                  # DocumentSource ABC
├── registry.py              # Plugin registry
├── factory.py               # Factory + GenericDocumentSource
├── federal.py               # Federal legislation
├── emissions.py             # Emissions reporting
├── state.py                 # State legislation
├── local_government.py      # Local government
└── README.md               # This file
```

## Examples

```bash
python examples/document_sources_demo.py
```
