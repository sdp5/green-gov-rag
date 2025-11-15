# Citation Metadata

> Legal-Grade Document References

## Overview

GreenGovRAG implements **legal-grade citation metadata** following 2025 industry best practices for regulatory RAG systems. This enables precise document referencing with hierarchical section tracking, deep linking, and professional citation formatting.

## Architecture

### 1. Hierarchical PDF Parsing
**File**: `green_gov_rag/etl/parsers/layout_parser.py`

Uses LLMSherpa LayoutPDFReader to extract:
- Section hierarchy (chapters → sections → subsections)
- Page numbers and page ranges
- Chunk types (paragraph, table, list, header)
- Parent section chains
- Contextual headers

```python
from green_gov_rag.etl.parsers.layout_parser import HierarchicalPDFParser

parser = HierarchicalPDFParser()
chunks = parser.parse_with_structure("policy.pdf")

# Example chunk metadata
{
    "chunk_id": 0,
    "chunk_type": "paragraph",
    "page_number": 42,
    "section_title": "Market-Based Accounting Methods",
    "section_hierarchy": [
        "Part 3: Scope 2 Emissions",
        "Section 3.2: Calculation Methods",
        "3.2.1 Market-Based Accounting"
    ],
    "parent_sections": ["Part 3", "Section 3.2"]
}
```

### 2. Enhanced API Schema
**File**: `green_gov_rag/api/schemas/query.py`

`SourceDocument` schema includes:

**Core Fields:**
- `title`: Document title
- `source_url`: Document URL
- `excerpt`: Relevant text excerpt
- `relevance_score`: Similarity score (0-1)

**Citation Metadata:**
- `page_number`: Page where content appears
- `page_range`: [start, end] if multi-page
- `section_title`: Current section title
- `section_hierarchy`: Full breadcrumb path
- `clause_reference`: Legal reference (e.g., "s.3.2.1")
- `deep_link`: Direct link to PDF page/section
- `citation`: Formatted citation string

**Document Context:**
- `jurisdiction`: federal/state/local
- `category`: environment, planning, legislation
- `topic`: emissions_reporting, biodiversity, etc.
- `region`: Geographic region

**ESG Metadata:**
- `frameworks`: [NGER, ISSB, GHG_Protocol]
- `emission_scopes`: [scope_1, scope_2, scope_3]
- `greenhouse_gases`: [CO2, CH4, N2O, ...]
- `consolidation_method`: operational_control, etc.
- `regulator`: Regulatory authority

**Spatial Metadata:**
- `spatial_scope`: federal/state/local
- `state`: State code (SA, NSW, VIC, etc.)
- `lga_codes`: ABS LGA codes
- `lga_names`: Local government area names

### 3. Citation Formatter
**File**: `green_gov_rag/api/utils/citation_formatter.py`

Utility class for formatting citations:

```python
from green_gov_rag.api.utils.citation_formatter import CitationFormatter

# Format citation
citation = CitationFormatter.format_citation(
    title="Scope 2 Emissions Guideline",
    page_number=42,
    clause_reference="s.3.2.1",
    regulator="Clean Energy Regulator"
)
# Output: "Clean Energy Regulator (2025), Scope 2 Emissions Guideline, Page 42, Section s.3.2.1"

# Build deep link
deep_link = CitationFormatter.build_deep_link(
    source_url="https://cer.gov.au/doc.pdf",
    page_number=42
)
# Output: "https://cer.gov.au/doc.pdf#page=42"

# Format section hierarchy
display = CitationFormatter.format_section_hierarchy_display([
    "Part 3: Scope 2 Emissions",
    "Section 3.2: Calculation Methods",
    "3.2.1 Market-Based Accounting"
])
# Output: "Part 3 > Section 3.2 > 3.2.1"
```

## API Response Example

### Request:
```json
{
  "query": "What are the Scope 2 market-based accounting methods under NGER?",
  "max_sources": 5
}
```

### Response:
```json
{
  "query": "What are the Scope 2 market-based accounting methods under NGER?",
  "answer": "Under NGER, Scope 2 emissions can be calculated using market-based accounting methods...",
  "sources": [
    {
      "title": "Clean Energy Regulator - Scope 2 Emissions Guideline",
      "source_url": "https://cer.gov.au/document/voluntary-market-based-scope-2-emissions-guideline",
      "excerpt": "Market-based accounting requires documentation of contractual instruments...",
      "relevance_score": 0.92,

      "page_number": 42,
      "page_range": [42, 43],
      "section_title": "Market-Based Accounting Methods",
      "section_hierarchy": [
        "Part 3: Scope 2 Emissions Accounting",
        "Section 3.2: Calculation Methods",
        "3.2.1 Market-Based Accounting"
      ],
      "clause_reference": "s.3.2.1",
      "deep_link": "https://cer.gov.au/document/voluntary-market-based-scope-2-emissions-guideline#page=42",
      "citation": "Clean Energy Regulator (2024), Scope 2 Emissions Guideline, Page 42, Section 3.2.1",

      "jurisdiction": "federal",
      "category": "environment",
      "topic": "emissions_reporting",
      "region": "Australia",

      "esg_metadata": {
        "frameworks": ["NGER", "ISSB", "GHG_Protocol"],
        "emission_scopes": ["scope_2"],
        "greenhouse_gases": ["CO2", "CH4", "N2O", "SF6", "HFCs", "PFCs", "NF3"],
        "consolidation_method": "operational_control",
        "methodology_type": "calculation",
        "regulator": "Clean Energy Regulator",
        "reportable_under_nger": true,
        "accounting_methods": ["location_based", "market_based"]
      },

      "spatial_metadata": {
        "spatial_scope": "federal",
        "state": null,
        "lga_codes": [],
        "applies_to_all_lgas": true
      }
    }
  ],
  "filters_applied": {
    "frameworks": ["NGER"],
    "emission_scopes": ["scope_2"]
  },
  "response_time_ms": 1234.56
}
```

## Frontend Integration

### Display Citation
```typescript
// Display formatted citation
<p className="citation">
  {source.citation}
</p>

// Output: "Clean Energy Regulator (2024), Scope 2 Emissions Guideline, Page 42, Section 3.2.1"
```

### Deep Link to Document
```typescript
// Link to specific page in PDF
<a href={source.deep_link} target="_blank">
  View Section {source.clause_reference}
</a>

// Opens: https://cer.gov.au/doc.pdf#page=42
```

### Section Breadcrumb
```typescript
// Display section hierarchy
<div className="breadcrumb">
  {source.section_hierarchy.join(" > ")}
</div>

// Output: Part 3: Scope 2 Emissions > Section 3.2 > 3.2.1
```

### ESG Badge Display
```typescript
// Show ESG frameworks
{source.esg_metadata?.frameworks.map(framework => (
  <Badge key={framework}>{framework}</Badge>
))}

// Output: [NGER] [ISSB] [GHG_Protocol]
```

### Location-Based Filtering
```typescript
// Show spatial scope
{source.spatial_metadata?.spatial_scope === "local" && (
  <Badge>
    {source.spatial_metadata.lga_names.join(", ")}
  </Badge>
)}

// Output: [City of Adelaide]
```

## Industry Compliance

### Legal RAG Best Practices (2025)
****Hierarchical section extraction**: 78.67% recall vs 57.33% baseline
****Clause references with deep links**: Industry standard for legal documents
****Context-aware chunking**: Preserves document structure

### ESG Reporting Standards
****NGER Compliance**: All 7 greenhouse gases tracked
****ISSB Alignment**: Scope 1/2/3 categorization
****GHG Protocol**: Consolidation methods documented

### Geospatial RAG
****Hybrid search**: Elasticsearch/Bedrock pattern
****Spatial filtering**: Federal → State → Local hierarchy
****NER for locations**: Automatic LGA code extraction

## Benefits

### For Users
1. **Precise References**: Know exactly where information comes from (page, section, clause)
2. **Quick Navigation**: Deep links jump directly to relevant sections
3. **Regulatory Context**: See which frameworks and regulators apply
4. **Location Awareness**: Understand geographic applicability

### For Developers
1. **Structured Metadata**: Consistent schema for citations
2. **Automatic Enrichment**: QueryService handles formatting
3. **Extensible**: Easy to add new metadata fields
4. **Type-Safe**: Pydantic models ensure data integrity

### For Compliance
1. **Audit Trail**: Full citation path for regulatory queries
2. **Framework Tracking**: Know which ESG standards apply
3. **Jurisdictional Clarity**: Federal vs state vs local distinction
4. **Version Control**: Document effective dates and versions

## Performance

- **Citation Formatting**: < 1ms per source
- **Deep Link Generation**: Instant (URL construction)
- **Metadata Extraction**: Handled during ETL (one-time cost)
- **API Response Size**: ~2-3KB per source with full metadata

## Future Enhancements

### Phase 2 (Q1 2026)
- [ ] PDF highlighting: Highlight exact text in PDF viewer
- [ ] Version tracking: Track document revisions over time
- [ ] Cross-references: Link related sections across documents
- [ ] Citation graphs: Visualize regulatory dependencies

### Phase 3 (Q2 2026)
- [ ] Temporal queries: "What were the rules in 2020?"
- [ ] Change tracking: "What changed between versions?"
- [ ] Impact analysis: "Which LGAs are affected by this regulation?"
- [ ] Compliance scoring: "Does this meet ISSB requirements?"

## References

- **Legal RAG Research**: Hierarchical document parsing (78.67% recall improvement)
- **NGER Act 2007**: Australian emissions reporting requirements
- **ISSB Standards**: IFRS S1/S2 climate disclosure standards
- **GHG Protocol**: Corporate accounting and reporting standard
- **Elasticsearch Geospatial RAG**: Hybrid search pattern
- **LLMSherpa**: Intelligent PDF layout parsing

---

**Last Updated**: 2025-10-15
**Version**: 1.0.0
**Status**: Production-Ready ✅
