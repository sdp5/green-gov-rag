# CLI Reference

> Complete command-line interface reference for GreenGovRAG

## Overview

The `greengovrag-cli` tool provides commands for ETL pipeline management, RAG queries, database operations, and system administration.

## Installation

```bash
# Install backend with CLI
cd backend
pip install -e .

# Verify installation
greengovrag-cli --version
```

## Global Options

Available for all commands:

```bash
greengovrag-cli [OPTIONS] COMMAND [ARGS]...

Options:
  --version              Show version and exit
  --help                 Show help message and exit
  --config PATH          Path to config file (default: .env)
  --verbose, -v          Enable verbose logging
  --quiet, -q            Suppress output (errors only)
```

## Commands

### `etl` - ETL Pipeline Management

Manage the extract, transform, load pipeline for document ingestion.

#### `etl run-pipeline`

Run the complete ETL pipeline.

```bash
greengovrag-cli etl run-pipeline [OPTIONS]

Options:
  --config PATH          Document sources config (default: configs/documents_config.yml)
  --force-reindex        Force re-embedding of existing documents
  --skip-download        Skip download, use existing files
  --sources TEXT         Comma-separated list of sources to process
  --parallel INT         Number of parallel workers (default: 4)
  --dry-run              Show what would be done without executing

Examples:
  # Run full pipeline
  greengovrag-cli etl run-pipeline

  # Force reindex all documents
  greengovrag-cli etl run-pipeline --force-reindex

  # Process only federal legislation
  greengovrag-cli etl run-pipeline --sources federal_legislation

  # Dry run to preview
  greengovrag-cli etl run-pipeline --dry-run
```

#### `etl download`

Download documents from configured sources.

```bash
greengovrag-cli etl download [OPTIONS]

Options:
  --config PATH          Document sources config
  --output-dir PATH      Download directory (default: data/raw)
  --sources TEXT         Comma-separated source types
  --verify               Verify downloads with checksums

Examples:
  # Download all documents
  greengovrag-cli etl download

  # Download only emissions data
  greengovrag-cli etl download --sources emissions_reporting

  # Download to custom directory
  greengovrag-cli etl download --output-dir /mnt/storage/docs
```

#### `etl chunk`

Chunk documents into smaller segments.

```bash
greengovrag-cli etl chunk [OPTIONS]

Options:
  --input-dir PATH       Input directory (default: data/raw)
  --output-dir PATH      Output directory (default: data/processed)
  --chunk-size INT       Chunk size in tokens (default: 500)
  --chunk-overlap INT    Overlap in tokens (default: 100)
  --parser TYPE          Parser type (auto, pdf, html, layout)

Examples:
  # Chunk all documents
  greengovrag-cli etl chunk

  # Custom chunk size
  greengovrag-cli etl chunk --chunk-size 1000 --chunk-overlap 200

  # Use layout parser for PDFs
  greengovrag-cli etl chunk --parser layout
```

#### `etl embed`

Generate embeddings for chunks.

```bash
greengovrag-cli etl embed [OPTIONS]

Options:
  --input-dir PATH       Chunked documents directory
  --model TEXT           Embedding model name
  --batch-size INT       Batch size (default: 100)
  --output-dir PATH      Output directory for embeddings

Examples:
  # Generate embeddings
  greengovrag-cli etl embed

  # Use different model
  greengovrag-cli etl embed --model sentence-transformers/all-mpnet-base-v2

  # Smaller batches for memory constraints
  greengovrag-cli etl embed --batch-size 32
```

#### `etl index`

Index embeddings into vector store.

```bash
greengovrag-cli etl index [OPTIONS]

Options:
  --input-dir PATH       Embeddings directory
  --vector-store TYPE    Vector store type (faiss, qdrant)
  --collection TEXT      Collection name (default: greengovrag)
  --force-recreate       Drop and recreate collection

Examples:
  # Index to Qdrant
  greengovrag-cli etl index --vector-store qdrant

  # Recreate index
  greengovrag-cli etl index --force-recreate
```

#### `etl validate`

Validate document sources configuration.

```bash
greengovrag-cli etl validate [OPTIONS]

Options:
  --config PATH          Document sources config
  --check-urls           Verify all URLs are accessible
  --strict               Fail on warnings

Examples:
  # Validate config
  greengovrag-cli etl validate

  # Check URL accessibility
  greengovrag-cli etl validate --check-urls

  # Strict mode (warnings as errors)
  greengovrag-cli etl validate --strict
```

### `rag` - RAG Query Commands

Query the RAG system from command line.

#### `rag query`

Perform a RAG query.

```bash
greengovrag-cli rag query [OPTIONS] QUERY

Arguments:
  QUERY                  Query text (required)

Options:
  --max-sources INT      Max source documents (default: 5)
  --lga-name TEXT        Filter by LGA name
  --lga-code INT         Filter by LGA code
  --jurisdiction TEXT    Filter by jurisdiction (federal, state, local)
  --output FORMAT        Output format (json, text, markdown)
  --save PATH            Save response to file

Examples:
  # Simple query
  greengovrag-cli rag query "What are NGER reporting requirements?"

  # With LGA filter
  greengovrag-cli rag query "Vegetation clearing rules" --lga-name "City of Adelaide"

  # JSON output
  greengovrag-cli rag query "EPBC Act requirements" --output json

  # Save to file
  greengovrag-cli rag query "Climate risk disclosure" --save response.md
```

#### `rag batch-query`

Run multiple queries from a file.

```bash
greengovrag-cli rag batch-query [OPTIONS] INPUT_FILE

Arguments:
  INPUT_FILE             File with queries (one per line)

Options:
  --output-dir PATH      Output directory for responses
  --format FORMAT        Output format (json, csv)
  --parallel INT         Parallel queries (default: 1)

Examples:
  # Process queries from file
  greengovrag-cli rag batch-query queries.txt

  # Parallel processing
  greengovrag-cli rag batch-query queries.txt --parallel 5

  # CSV output
  greengovrag-cli rag batch-query queries.txt --format csv
```

#### `rag test`

Test RAG system with sample queries.

```bash
greengovrag-cli rag test [OPTIONS]

Options:
  --suite TEXT           Test suite (basic, comprehensive, stress)
  --output PATH          Test results file

Examples:
  # Run basic tests
  greengovrag-cli rag test

  # Comprehensive test suite
  greengovrag-cli rag test --suite comprehensive

  # Save results
  greengovrag-cli rag test --output test_results.json
```

### `db` - Database Management

Manage database schema and data.

#### `db init`

Initialize database schema.

```bash
greengovrag-cli db init [OPTIONS]

Options:
  --drop-existing        Drop existing tables (DANGER!)
  --seed                 Seed with sample data

Examples:
  # Initialize database
  greengovrag-cli db init

  # Drop and recreate
  greengovrag-cli db init --drop-existing

  # With sample data
  greengovrag-cli db init --seed
```

#### `db migrate`

Run database migrations.

```bash
greengovrag-cli db migrate [OPTIONS] [REVISION]

Arguments:
  REVISION               Target revision (default: head)

Options:
  --sql                  Show SQL without executing
  --autogenerate         Auto-generate migration from models

Examples:
  # Migrate to latest
  greengovrag-cli db migrate

  # Migrate to specific revision
  greengovrag-cli db migrate abc123

  # Show SQL only
  greengovrag-cli db migrate --sql

  # Auto-generate migration
  greengovrag-cli db migrate --autogenerate
```

#### `db rollback`

Rollback database migration.

```bash
greengovrag-cli db rollback [OPTIONS]

Options:
  --steps INT            Number of steps to rollback (default: 1)
  --revision TEXT        Rollback to specific revision

Examples:
  # Rollback one migration
  greengovrag-cli db rollback

  # Rollback 3 migrations
  greengovrag-cli db rollback --steps 3

  # Rollback to specific revision
  greengovrag-cli db rollback --revision abc123
```

#### `db export`

Export database to file.

```bash
greengovrag-cli db export [OPTIONS] OUTPUT_FILE

Arguments:
  OUTPUT_FILE            Export file path

Options:
  --format FORMAT        Export format (sql, json, csv)
  --tables TEXT          Comma-separated table names (default: all)
  --compress             Compress output (gzip)

Examples:
  # Export to SQL
  greengovrag-cli db export backup.sql

  # Export to JSON
  greengovrag-cli db export data.json --format json

  # Export specific tables
  greengovrag-cli db export docs.sql --tables documents,chunks

  # Compressed export
  greengovrag-cli db export backup.sql.gz --compress
```

#### `db import`

Import database from file.

```bash
greengovrag-cli db import [OPTIONS] INPUT_FILE

Arguments:
  INPUT_FILE             Import file path

Options:
  --format FORMAT        Import format (auto-detect from extension)
  --drop-tables          Drop existing tables before import
  --skip-errors          Continue on errors

Examples:
  # Import from SQL
  greengovrag-cli db import backup.sql

  # Drop existing data
  greengovrag-cli db import backup.sql --drop-tables

  # Import JSON
  greengovrag-cli db import data.json
```

### `vector-store` - Vector Store Management

Manage vector store operations.

#### `vector-store info`

Show vector store information.

```bash
greengovrag-cli vector-store info [OPTIONS]

Options:
  --collection TEXT      Collection name (default: greengovrag)

Examples:
  # Show info
  greengovrag-cli vector-store info

  # Specific collection
  greengovrag-cli vector-store info --collection test_collection
```

#### `vector-store backup`

Backup vector store.

```bash
greengovrag-cli vector-store backup [OPTIONS] OUTPUT_PATH

Arguments:
  OUTPUT_PATH            Backup file path

Options:
  --collection TEXT      Collection name
  --compress             Compress backup

Examples:
  # Backup to file
  greengovrag-cli vector-store backup qdrant_backup.tar

  # Compressed backup
  greengovrag-cli vector-store backup qdrant_backup.tar.gz --compress
```

#### `vector-store restore`

Restore vector store from backup.

```bash
greengovrag-cli vector-store restore [OPTIONS] INPUT_PATH

Arguments:
  INPUT_PATH             Backup file path

Options:
  --collection TEXT      Collection name
  --overwrite            Overwrite existing collection

Examples:
  # Restore from backup
  greengovrag-cli vector-store restore qdrant_backup.tar

  # Overwrite existing
  greengovrag-cli vector-store restore qdrant_backup.tar --overwrite
```

#### `vector-store migrate`

Migrate between vector stores.

```bash
greengovrag-cli vector-store migrate [OPTIONS]

Options:
  --from-type TYPE       Source vector store (faiss, qdrant)
  --to-type TYPE         Target vector store
  --collection TEXT      Collection name

Examples:
  # Migrate FAISS to Qdrant
  greengovrag-cli vector-store migrate --from-type faiss --to-type qdrant
```

### `admin` - Administration Commands

System administration and maintenance.

#### `admin health`

Check system health.

```bash
greengovrag-cli admin health [OPTIONS]

Options:
  --json                 Output as JSON
  --verbose              Detailed health check

Examples:
  # Health check
  greengovrag-cli admin health

  # JSON output
  greengovrag-cli admin health --json

  # Verbose
  greengovrag-cli admin health --verbose
```

#### `admin clear-cache`

Clear query result cache.

```bash
greengovrag-cli admin clear-cache [OPTIONS]

Options:
  --pattern TEXT         Clear keys matching pattern
  --older-than TEXT      Clear entries older than (e.g., '24h', '7d')

Examples:
  # Clear all cache
  greengovrag-cli admin clear-cache

  # Clear old entries
  greengovrag-cli admin clear-cache --older-than 7d

  # Pattern matching
  greengovrag-cli admin clear-cache --pattern "query:*"
```

#### `admin stats`

Show system statistics.

```bash
greengovrag-cli admin stats [OPTIONS]

Options:
  --format FORMAT        Output format (text, json)
  --period TEXT          Time period (1h, 24h, 7d, 30d)

Examples:
  # Show stats
  greengovrag-cli admin stats

  # Last 7 days
  greengovrag-cli admin stats --period 7d

  # JSON output
  greengovrag-cli admin stats --format json
```

#### `admin cleanup`

Clean up old data.

```bash
greengovrag-cli admin cleanup [OPTIONS]

Options:
  --older-than TEXT      Delete data older than
  --table TEXT           Specific table to clean
  --dry-run              Show what would be deleted

Examples:
  # Cleanup old logs (30+ days)
  greengovrag-cli admin cleanup --older-than 30d

  # Dry run
  greengovrag-cli admin cleanup --older-than 90d --dry-run

  # Specific table
  greengovrag-cli admin cleanup --table query_logs --older-than 7d
```

## Configuration File

Use a custom configuration file:

```bash
# Create config file
cat > custom.env << EOF
DATABASE_URL=postgresql://user:pass@localhost/db
VECTOR_STORE_TYPE=qdrant
LLM_PROVIDER=openai
EOF

# Use with CLI
greengovrag-cli --config custom.env etl run-pipeline
```

## Output Formats

### JSON

```bash
greengovrag-cli rag query "test" --output json
```

```json
{
  "query": "test",
  "answer": "...",
  "sources": [...],
  "trust_score": 0.85
}
```

### Markdown

```bash
greengovrag-cli rag query "test" --output markdown
```

```markdown
# Query: test

## Answer
...

## Sources
1. [Document Title](url)
   - Relevance: 0.92
   - Page: 42
```

### Text (Default)

```bash
greengovrag-cli rag query "test"
```

```
Query: test

Answer:
...

Sources:
- Document Title (relevance: 0.92)
  Page 42, Section 3.2.1
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Database error |
| 4 | Vector store error |
| 5 | LLM provider error |
| 130 | Interrupted (Ctrl+C) |

## Environment Variables

CLI respects all configuration environment variables. See [Configuration Reference](config-reference.md).

## Examples

### Complete ETL Workflow

```bash
# 1. Validate config
greengovrag-cli etl validate --check-urls

# 2. Download documents
greengovrag-cli etl download

# 3. Chunk documents
greengovrag-cli etl chunk

# 4. Generate embeddings
greengovrag-cli etl embed

# 5. Index to vector store
greengovrag-cli etl index

# Or run all at once
greengovrag-cli etl run-pipeline
```

### RAG Query Workflow

```bash
# Query with filters
greengovrag-cli rag query \
  "NGER reporting requirements" \
  --lga-name "Adelaide" \
  --max-sources 10 \
  --output json \
  --save response.json
```

### Database Maintenance

```bash
# Backup database
greengovrag-cli db export backup.sql --compress

# Run migrations
greengovrag-cli db migrate

# Check health
greengovrag-cli admin health --verbose

# Cleanup old data
greengovrag-cli admin cleanup --older-than 90d --dry-run
```

### Vector Store Migration

```bash
# Backup current store
greengovrag-cli vector-store backup faiss_backup.tar.gz --compress

# Migrate to Qdrant
greengovrag-cli vector-store migrate \
  --from-type faiss \
  --to-type qdrant

# Verify migration
greengovrag-cli vector-store info
```

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
