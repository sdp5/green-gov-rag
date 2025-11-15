# Database Schema

> Complete PostgreSQL database schema reference

## Overview

GreenGovRAG uses PostgreSQL 15+ with the `pgvector` extension for hybrid search capabilities. The schema is managed using Alembic migrations.

## Tables

### `documents`

Stores metadata for source regulatory documents.

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    source_url VARCHAR(1000),
    source_type VARCHAR(100) NOT NULL,  -- federal_legislation, emissions_reporting, etc.
    jurisdiction VARCHAR(50),            -- federal, state, local
    category VARCHAR(100),               -- environment, legislation, planning
    topic VARCHAR(100),                  -- emissions_reporting, biodiversity, etc.
    region VARCHAR(100),                 -- Australia, NSW, SA, etc.
    file_path VARCHAR(1000),
    file_hash VARCHAR(64),
    file_size_bytes BIGINT,
    publication_date DATE,
    effective_date DATE,
    version VARCHAR(50),
    metadata JSONB,                      -- Flexible metadata storage
    spatial_metadata JSONB,              -- LGA codes, state, spatial scope
    esg_metadata JSONB,                  -- ESG frameworks, scopes, gases
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_jurisdiction ON documents(jurisdiction);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_topic ON documents(topic);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);
CREATE INDEX idx_documents_spatial_metadata ON documents USING GIN(spatial_metadata);
CREATE INDEX idx_documents_esg_metadata ON documents USING GIN(esg_metadata);
```

**Columns**:
- `id`: Primary key
- `title`: Document title
- `source_url`: Original URL
- `source_type`: Plugin type that processed this document
- `jurisdiction`: federal | state | local
- `category`: Document category
- `topic`: Document topic/subject
- `region`: Geographic region
- `file_path`: Local/cloud storage path
- `file_hash`: SHA-256 hash for deduplication
- `file_size_bytes`: File size
- `publication_date`: When published
- `effective_date`: When became effective
- `version`: Document version
- `metadata`: General metadata (JSONB)
- `spatial_metadata`: Geographic metadata (JSONB)
- `esg_metadata`: ESG-specific metadata (JSONB)
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

**Example Row**:
```json
{
  "id": 1,
  "title": "Clean Energy Regulator - Scope 2 Emissions Guideline",
  "source_url": "https://cer.gov.au/document/...",
  "source_type": "emissions_reporting",
  "jurisdiction": "federal",
  "category": "environment",
  "topic": "emissions_reporting",
  "region": "Australia",
  "metadata": {
    "author": "Clean Energy Regulator",
    "language": "en"
  },
  "esg_metadata": {
    "frameworks": ["NGER", "ISSB"],
    "emission_scopes": ["scope_2"],
    "greenhouse_gases": ["CO2", "CH4", "N2O"]
  }
}
```

### `chunks`

Stores processed text chunks with embeddings.

```sql
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    chunk_type VARCHAR(50),              -- paragraph, table, list, header
    page_number INTEGER,
    page_range INTEGER[],
    section_title VARCHAR(500),
    section_hierarchy TEXT[],            -- Breadcrumb path
    parent_sections TEXT[],
    clause_reference VARCHAR(100),       -- e.g., "s.3.2.1"
    token_count INTEGER,
    embedding vector(384),               -- pgvector extension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_page_number ON chunks(page_number);
CREATE INDEX idx_chunks_metadata ON chunks USING GIN(metadata);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat(embedding vector_cosine_ops)
    WITH (lists = 100);  -- Adjust based on data size
```

**Columns**:
- `id`: Primary key
- `document_id`: Foreign key to documents table
- `chunk_index`: Position in document (0-indexed)
- `content`: Chunked text content
- `chunk_type`: Type of content (paragraph, table, list, header)
- `page_number`: Page where chunk appears
- `page_range`: Multi-page chunks [start, end]
- `section_title`: Current section title
- `section_hierarchy`: Full breadcrumb path
- `parent_sections`: Parent section titles
- `clause_reference`: Legal reference (e.g., "s.3.2.1")
- `token_count`: Number of tokens in chunk
- `embedding`: Vector embedding (pgvector)
- `metadata`: Chunk-specific metadata
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

**Example Row**:
```json
{
  "id": 42,
  "document_id": 1,
  "chunk_index": 15,
  "content": "Market-based accounting requires documentation...",
  "chunk_type": "paragraph",
  "page_number": 42,
  "section_title": "Market-Based Accounting Methods",
  "section_hierarchy": [
    "Part 3: Scope 2 Emissions",
    "Section 3.2: Calculation Methods",
    "3.2.1 Market-Based Accounting"
  ],
  "clause_reference": "s.3.2.1",
  "token_count": 485
}
```

### `query_logs`

Tracks all RAG queries for analytics.

```sql
CREATE TABLE query_logs (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64),              -- MD5 hash for deduplication
    response_text TEXT,
    sources_count INTEGER,
    trust_score NUMERIC(3, 2),           -- 0.00 - 1.00
    response_time_ms NUMERIC(10, 2),
    cache_hit BOOLEAN DEFAULT FALSE,
    filters JSONB,                       -- Applied filters (LGA, jurisdiction, etc.)
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_query_logs_query_hash ON query_logs(query_hash);
CREATE INDEX idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX idx_query_logs_session_id ON query_logs(session_id);
CREATE INDEX idx_query_logs_created_at ON query_logs(created_at DESC);
CREATE INDEX idx_query_logs_filters ON query_logs USING GIN(filters);
```

**Columns**:
- `id`: Primary key
- `query_text`: User query
- `query_hash`: MD5 hash for cache lookup
- `response_text`: Generated answer
- `sources_count`: Number of source documents used
- `trust_score`: Response confidence (0.00-1.00)
- `response_time_ms`: Query processing time
- `cache_hit`: Whether response was cached
- `filters`: Applied filters (JSONB)
- `user_id`: User identifier (if authenticated)
- `session_id`: Session identifier
- `ip_address`: Client IP address
- `user_agent`: Client user agent
- `created_at`: Query timestamp

### `query_sources`

Junction table linking queries to source documents.

```sql
CREATE TABLE query_sources (
    id SERIAL PRIMARY KEY,
    query_log_id INTEGER NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    relevance_score NUMERIC(5, 4),       -- 0.0000 - 1.0000
    rank_position INTEGER,               -- 1, 2, 3, ...
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_query_sources_query_log_id ON query_sources(query_log_id);
CREATE INDEX idx_query_sources_chunk_id ON query_sources(chunk_id);
```

**Columns**:
- `id`: Primary key
- `query_log_id`: Foreign key to query_logs
- `chunk_id`: Foreign key to chunks
- `relevance_score`: Similarity score
- `rank_position`: Position in results (1=top)
- `created_at`: Record creation timestamp

### `cache`

Query result cache (alternative to Redis/DynamoDB).

```sql
CREATE TABLE cache (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_cache_expires_at ON cache(expires_at);
```

**Columns**:
- `key`: Cache key (query hash)
- `value`: Cached response (JSONB)
- `expires_at`: Expiration timestamp
- `created_at`: Record creation timestamp

**Cleanup Query** (run periodically):
```sql
DELETE FROM cache WHERE expires_at < NOW();
```

### `lga_boundaries`

Local Government Area boundary data.

```sql
CREATE TABLE lga_boundaries (
    id SERIAL PRIMARY KEY,
    lga_code INTEGER NOT NULL UNIQUE,   -- ABS LGA code
    lga_name VARCHAR(200) NOT NULL,
    state VARCHAR(3) NOT NULL,           -- NSW, VIC, SA, etc.
    geometry GEOMETRY(MultiPolygon, 4326),  -- PostGIS extension
    area_sqkm NUMERIC(10, 2),
    population INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_lga_boundaries_lga_code ON lga_boundaries(lga_code);
CREATE INDEX idx_lga_boundaries_state ON lga_boundaries(state);
CREATE INDEX idx_lga_boundaries_geometry ON lga_boundaries USING GIST(geometry);
```

**Columns**:
- `id`: Primary key
- `lga_code`: ABS LGA code (unique)
- `lga_name`: LGA name
- `state`: State abbreviation
- `geometry`: Geographic boundary (PostGIS)
- `area_sqkm`: Area in square kilometers
- `population`: Population (latest census)
- `metadata`: Additional metadata
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

## Views

### `document_stats`

Aggregated document statistics.

```sql
CREATE VIEW document_stats AS
SELECT
    source_type,
    jurisdiction,
    category,
    COUNT(*) AS document_count,
    SUM(file_size_bytes) AS total_size_bytes,
    MIN(publication_date) AS earliest_publication,
    MAX(publication_date) AS latest_publication
FROM documents
GROUP BY source_type, jurisdiction, category;
```

### `query_analytics`

Query analytics for the last 30 days.

```sql
CREATE VIEW query_analytics AS
SELECT
    DATE(created_at) AS query_date,
    COUNT(*) AS total_queries,
    AVG(trust_score) AS avg_trust_score,
    AVG(response_time_ms) AS avg_response_time_ms,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::FLOAT / COUNT(*) AS cache_hit_rate
FROM query_logs
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY query_date DESC;
```

### `popular_queries`

Most frequent queries in the last 7 days.

```sql
CREATE VIEW popular_queries AS
SELECT
    query_hash,
    MAX(query_text) AS query_text,  -- Get one example
    COUNT(*) AS query_count,
    AVG(trust_score) AS avg_trust_score
FROM query_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY query_hash
ORDER BY query_count DESC
LIMIT 100;
```

## Functions

### `update_updated_at()`

Automatically update `updated_at` timestamp.

```sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables
CREATE TRIGGER documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER chunks_updated_at
BEFORE UPDATE ON chunks
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

### `calculate_trust_score()`

Calculate trust score based on source relevance.

```sql
CREATE OR REPLACE FUNCTION calculate_trust_score(relevance_scores NUMERIC[])
RETURNS NUMERIC AS $$
DECLARE
    avg_score NUMERIC;
    top_score NUMERIC;
BEGIN
    IF array_length(relevance_scores, 1) = 0 THEN
        RETURN 0.0;
    END IF;

    -- Weighted average: 60% top score, 40% average of all
    avg_score := (SELECT AVG(score) FROM unnest(relevance_scores) AS score);
    top_score := (SELECT MAX(score) FROM unnest(relevance_scores) AS score);

    RETURN ROUND(0.6 * top_score + 0.4 * avg_score, 2);
END;
$$ LANGUAGE plpgsql;
```

## Migrations

### Create Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add section_hierarchy to chunks"

# Create empty migration
alembic revision -m "Add custom index"
```

### Migration Structure

```python
# alembic/versions/abc123_add_section_hierarchy.py

def upgrade():
    """Upgrade database schema."""
    op.add_column('chunks',
        sa.Column('section_hierarchy', ARRAY(sa.String), nullable=True)
    )

def downgrade():
    """Downgrade database schema."""
    op.drop_column('chunks', 'section_hierarchy')
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# View current version
alembic current

# View migration history
alembic history
```

## Useful Queries

### Document Count by Jurisdiction

```sql
SELECT
    jurisdiction,
    COUNT(*) AS document_count
FROM documents
GROUP BY jurisdiction
ORDER BY document_count DESC;
```

### Top 10 Most-Used Source Documents

```sql
SELECT
    d.title,
    COUNT(qs.id) AS usage_count,
    AVG(qs.relevance_score) AS avg_relevance
FROM documents d
JOIN chunks c ON c.document_id = d.id
JOIN query_sources qs ON qs.chunk_id = c.id
WHERE qs.created_at > NOW() - INTERVAL '30 days'
GROUP BY d.id, d.title
ORDER BY usage_count DESC
LIMIT 10;
```

### Average Trust Score by Topic

```sql
SELECT
    (filters->>'topic') AS topic,
    AVG(trust_score) AS avg_trust_score,
    COUNT(*) AS query_count
FROM query_logs
WHERE filters IS NOT NULL
GROUP BY (filters->>'topic')
ORDER BY avg_trust_score DESC;
```

### Slow Queries

```sql
SELECT
    query_text,
    response_time_ms,
    sources_count,
    created_at
FROM query_logs
WHERE response_time_ms > 2000
ORDER BY response_time_ms DESC
LIMIT 20;
```

### Cache Hit Rate

```sql
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS total_queries,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
    ROUND(100.0 * SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) / COUNT(*), 2) AS hit_rate_pct
FROM query_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## Performance Tuning

### Vacuum and Analyze

```sql
-- Full vacuum (requires table lock)
VACUUM FULL documents;

-- Regular vacuum (no lock)
VACUUM ANALYZE documents;

-- Auto-vacuum settings (in postgresql.conf)
autovacuum = on
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_scale_factor = 0.05
```

### Index Maintenance

```sql
-- Rebuild index
REINDEX INDEX idx_chunks_embedding;

-- Rebuild all indexes on table
REINDEX TABLE chunks;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Connection Pooling

```python
# In SQLModel engine configuration
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
