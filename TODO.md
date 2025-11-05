# GreenGovRAG - TODO & Future Enhancements

### 1. Scalable Document Source Management
**Problem**: Currently requires manual YAML editing (`documents_config.yml`) for each new document source - not scalable.

**Current Limitations**:
- Manual YAML editing required for each new source
- No auto-discovery of new documents from monitored websites
- GitHub commit required to add documents
- No web UI for adding sources
- Difficult for non-technical contributors

**Proposed Solutions**:

#### Option 1: Database-backed Source Registry
Store document sources in PostgreSQL instead of YAML:
- New table: `document_sources` (id, name, source_type, base_url, enabled, config JSONB)
- Admin API endpoints for CRUD operations
- ETL reads from DB instead of YAML
- Web UI for adding/editing sources

#### Option 2: Auto-Discovery with Scrapers
Implement `MonitorableSource` for key sources:
```python
class EPAMonitor(MonitorableSource):
    def discover_documents(self) -> List[DocumentMetadata]:
        # Scrape EPA website for new PDFs
        # Check if URL changed
        # Auto-detect new versions
```

#### Option 3: Hybrid Approach
**Tier 1**: Critical sources - Auto-monitored with scrapers
- Federal legislation (legislation.gov.au)
- State EPA guidelines
- NGER reports

**Tier 2**: Standard sources - Database-backed, manually added via admin UI
- Council planning schemes
- Industry guidelines

**Tier 3**: Contributed sources - GitHub issues → automated ingestion
- Community contributions
- One-off documents

**Quick Win**: Implement database-backed source registry with admin API endpoints.

---

### 2. Auto-Location Extraction for Queries
**Status**: Infrastructure implemented but **DISABLED** (needs better document coverage)

**Current Implementation**:
- `HybridGeospatialSearch.search_with_auto_location()` - uses NER to extract locations
- `RAGChain.retrieve_documents(use_auto_location=True)` - passes flag through
- `QueryService` - has integration point (line 173: `use_auto_location = False`)

**Why Disabled**:
Auto-location filtering can be too narrow when document coverage is limited, resulting in empty source lists. The LLM still generates reasonable answers but without citations (trust score drops).

**Auto-Location Queries** (when enabled):
- "What are tree clearing rules in Adelaide?" → Auto-extracts "Adelaide" LGA
- "Emission rules in Port Adelaide Enfield" → Auto-extracts "Port Adelaide Enfield" LGA
- "Building rules in NSW" → Auto-extracts "NSW" state

**To Enable Later**:
When document coverage improves, change line 173 in `query_service.py`:
```python
# Change from:
use_auto_location = False

# To:
use_auto_location = not normalized_lgas and not normalized_region
```

**Better Approach**: Make it configurable in `config.py`:
```python
enable_auto_location: bool = Field(
    default=False,
    description="Enable automatic location extraction from queries"
)
```

---

### 3. Parcel-level Geospatial Queries
- Currently LGA-level only
- Add support for specific address/parcel queries

### 4. Export Features
- Export query responses to PDF/DOCX reports
- Bulk export capabilities

### 5. Advanced Monitoring
- Prometheus + Grafana integration
- Enhanced alerting and dashboards
