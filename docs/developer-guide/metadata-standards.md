# Metadata Enhancement

Industry-standard metadata for legal/regulatory RAG with ESG and geospatial capabilities.

## Implementation Overview

| Component | Description |
|-----------|-------------|
| Hierarchical PDF Parsing | LLMSherpa-based section extraction with page tracking |
| ESG Metadata | NGER/ISSB-compliant emission tracking |
| Spatial Metadata | LGA-aware filtering with ABS codes |
| Enhanced Chunking | Hierarchy-preserving text splitting |

## 1. Hierarchical PDF Parsing

### File
`green_gov_rag/etl/parsers/layout_parser.py`

### Features
- Section hierarchy extraction (chapter → section → subsection)
- Page number tracking for citations
- Chunk type detection (paragraph, table, list, header)
- Context preservation (section headers included)

### Example Output

```python
{
    "content": "Market-based accounting requires...",
    "metadata": {
        "chunk_id": 42,
        "chunk_type": "paragraph",
        "page_number": 15,
        "section_hierarchy": ["Part 3: Scope 2", "Section 3.2", "3.2.1 Methods"],
        "section_title": "3.2.1 Market-Based Methods",
        "section_level": 3,
        "parent_sections": ["Part 3: Scope 2", "Section 3.2"]
    }
}
```

### Why It Matters
- 78.67% recall vs 57.33% baseline (industry standard)
- Precise citations: "Page 15, Section 3.2.1"
- Preserves document structure

## 2. ESG Metadata (NGER/ISSB)

### File
`configs/documents_config.yml`

### Schema

```yaml
esg_metadata:
  frameworks: [NGER, ISSB, GHG_Protocol]
  emission_scopes: [scope_1, scope_2, scope_3]
  greenhouse_gases: [CO2, CH4, N2O, SF6, HFCs, PFCs, NF3]
  consolidation_method: operational_control  # or equity_share, financial_control
  methodology_type: calculation
  reportable_under_nger: true
  scope_3_reportable: false
  regulator: Clean Energy Regulator
  regulation_type: guideline
  activity_types: [fuel_combustion, fugitive_emissions]
  facility_types: [coal_mine]
  industry_codes: [B0600]  # ANZSIC codes
```

### Enhanced Documents
- Clean Energy Regulator - Scope 1 Coal Mining Guideline
- Clean Energy Regulator - Scope 2 Emissions Guideline
- Clean Energy Regulator - Fuel Combustion Guideline
- Clean Energy Regulator - HFC & SF6 Gases Guideline

### Why It Matters
- NGER compliance: Tracks all 7 greenhouse gases
- ISSB alignment: Consolidation methods + Scope 3
- Enables ESG-specific queries

## 3. Spatial Metadata

### Schema

```yaml
spatial_metadata:
  spatial_scope: federal  # or state, local
  state: SA  # For state-level (null for federal)
  lga_codes: [40070, 40280]  # ABS LGA codes
  lga_names: [City of Adelaide, Port Adelaide Enfield]
  applies_to_all_lgas: false  # true for state/federal
  applies_to_point: false  # vs polygon
```

### Why It Matters
- Enables "click LGA, get policies" use case
- Hierarchical filtering: federal → state → local
- Foundation for hybrid geospatial RAG

## 4. Enhanced Chunking

### File
`green_gov_rag/etl/chunker.py`

### Method
`chunk_with_hierarchy()`

### Features
- Preserves all hierarchical metadata
- Creates unique chunk IDs across sub-chunks
- Tracks sub-chunk position within sections

### Usage

```python
from green_gov_rag.etl.parsers.layout_parser import HierarchicalPDFParser
from green_gov_rag.etl.chunker import TextChunker

# Parse with hierarchy
parser = HierarchicalPDFParser()
hierarchical_chunks = parser.parse_with_structure("policy.pdf")

# Chunk while preserving hierarchy
chunker = TextChunker(chunk_size=1000, chunk_overlap=100)
final_chunks = chunker.chunk_with_hierarchy(hierarchical_chunks)
```

## Integration

### ETL Pipeline

```python
from green_gov_rag.etl.parsers.layout_parser import HierarchicalPDFParser
from green_gov_rag.etl.chunker import TextChunker

# Parse with hierarchy
parser = HierarchicalPDFParser()
hierarchical_chunks = parser.parse_with_structure(
    pdf_path="document.pdf",
    base_metadata={
        "jurisdiction": "federal",
        "topic": "emissions_reporting",
        "esg_metadata": {...},
        "spatial_metadata": {...}
    }
)

# Chunk
chunker = TextChunker(chunk_size=1000, chunk_overlap=100)
final_chunks = chunker.chunk_with_hierarchy(hierarchical_chunks)
```

### Query/Retrieval

```python
# ESG-filtered query
results = vector_store.similarity_search(
    query="What are Scope 2 reporting requirements?",
    metadata_filters={
        "esg_metadata.emission_scopes": "scope_2",
        "esg_metadata.frameworks": "ISSB"
    }
)

# Spatial-filtered query
results = vector_store.similarity_search(
    query="What are tree preservation rules?",
    metadata_filters={
        "spatial_metadata.lga_codes": "50280"  # City of Adelaide
    }
)
```

## Benefits

| Benefit | Impact |
|---------|--------|
| Citation Quality | Page numbers + section hierarchy |
| ESG Compliance | NGER + ISSB framework alignment |
| Geo-Aware Filtering | LGA code support, hierarchical scope |
| Industry Standards | Legal RAG + ESG + Geospatial best practices |

## Example Responses

### ESG Query

```json
{
  "query": "What are Scope 2 market-based methods?",
  "answer": "Market-based accounting for Scope 2 emissions...",
  "sources": [{
    "title": "CER - Scope 2 Emissions Guideline",
    "citation": "CER (2024), Page 42, Section 3.2.1",
    "url": "https://cer.gov.au/...",
    "section_hierarchy": ["Part 3", "Section 3.2", "3.2.1 Methods"],
    "metadata": {
      "page_number": 42,
      "emission_scope": "scope_2",
      "frameworks": ["NGER", "ISSB"]
    }
  }]
}
```

### Spatial Query

```json
{
  "query": "Biodiversity rules in Adelaide?",
  "spatial_query": {
    "lga_code": "40070",
    "lga_name": "City of Adelaide"
  },
  "sources": [
    {
      "title": "City of Adelaide Development Guidelines",
      "spatial_scope": "local",
      "lga_codes": ["40070"],
      "applies_to_all_lgas": false
    },
    {
      "title": "Native Vegetation Guidelines (SA)",
      "spatial_scope": "state",
      "state": "SA",
      "applies_to_all_lgas": true
    },
    {
      "title": "EPBC Act",
      "spatial_scope": "federal",
      "applies_to_all_lgas": true
    }
  ]
}
```

## Files Modified

1. `pyproject.toml` - Added llmsherpa dependency
2. `green_gov_rag/etl/parsers/layout_parser.py` - NEW
3. `green_gov_rag/etl/chunker.py` - Added chunk_with_hierarchy()
4. `green_gov_rag/etl/ingest.py` - ESG/spatial metadata support
5. `configs/documents_config.yml` - Enhanced with NGER/ISSB metadata

## Status

- Implementation: Complete
- Type Checking: Passing
- Linting: Passing
- Ready for Testing: Yes

## See Also

- [Data Sources](./DATA.md) - Document sources and metadata
- [Plugin Architecture](./PLUGIN_ARCHITECTURE_SUMMARY.md) - Document source plugins
- [Project Structure](./PROJECT.md) - Repository organization
