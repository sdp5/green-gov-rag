# Document Sources

> Understanding the regulatory documents available in GreenGovRAG

See [Reference: Data Sources](../reference/data-sources.md) for the complete catalog of available documents.

## Overview

GreenGovRAG indexes Australian environmental and planning regulations from multiple jurisdictions:

- **Federal**: EPBC Act, NGER, emissions reporting
- **State**: NSW, VIC, SA, QLD planning and environment legislation
- **Local**: Council planning schemes and development controls
- **Industry**: ESG reporting frameworks (ISSB, TCFD, SASB)

## Document Categories

### Legislation

Primary laws and acts:
- Environment Protection and Biodiversity Conservation Act 1999 (EPBC)
- National Greenhouse and Energy Reporting Act 2007 (NGER)
- State environment protection acts
- Planning and development acts

### Guidelines and Policies

Regulatory guidance:
- NGER Technical Guidelines
- EPBC Referral Guidelines
- State-specific assessment guidelines
- Council development control plans

### Reporting Standards

Emissions and ESG frameworks:
- ISSB Climate Standards (IFRS S1, S2)
- TCFD Recommendations
- SASB Standards
- National Greenhouse Accounts

## Viewing Available Documents

### API Endpoint

```bash
curl http://localhost:8000/api/documents \
  -H "X-API-Key: your-secret-key-here"
```

Response:
```json
{
  "documents": [
    {
      "id": "epbc-act-2024",
      "title": "Environment Protection and Biodiversity Conservation Act 1999",
      "jurisdiction": "Federal",
      "document_type": "legislation",
      "last_updated": "2024-01-15",
      "chunk_count": 1523,
      "coverage": ["biodiversity", "heritage", "water", "land"]
    }
  ],
  "total": 42
}
```

### Filter by Jurisdiction

```bash
curl "http://localhost:8000/api/documents?jurisdiction=NSW" \
  -H "X-API-Key: your-secret-key-here"
```

### Filter by Type

```bash
curl "http://localhost:8000/api/documents?type=guidelines" \
  -H "X-API-Key: your-secret-key-here"
```

## Document Metadata

Each document includes:

| Field | Description |
|-------|-------------|
| `title` | Official document title |
| `jurisdiction` | Federal, State (NSW, VIC, etc.), or Local |
| `document_type` | legislation, guidelines, standards, scheme |
| `authority` | Publishing authority |
| `last_updated` | Date of last amendment/update |
| `coverage` | Topic tags (emissions, biodiversity, etc.) |
| `chunk_count` | Number of searchable chunks |
| `lga` | Applicable Local Government Areas |

## Adding Documents

For contributors looking to add new document sources, see:

- [Contributor Guide](../contributor-guide/overview.md)
- [Developer Guide: Plugin Architecture](../developer-guide/architecture/plugin-system.md)
- [Plugin API Reference](../reference/plugin-api.md)

## Data Sovereignty

All documents are stored and processed in Australia (ap-southeast-2 region) to comply with data sovereignty requirements.

See [Reference: Data Sources](../reference/data-sources.md) for sovereignty details.

## See Also

- [Reference: Complete Data Sources Catalog](../reference/data-sources.md)
- [Query documents by jurisdiction](querying.md#geospatial-filtering)
- [Add custom document sources](../contributor-guide/overview.md)
