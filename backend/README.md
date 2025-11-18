# GreenGovRAG Backend

Python backend with FastAPI, RAG (Retrieval-Augmented Generation), ETL pipeline, and multi-cloud support for querying Australian environmental regulations.

## Quick Start

```bash
# Install dependencies
cd backend
pip install -e .[dev]

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# Initialize database
alembic upgrade head

# Run API server
uvicorn green_gov_rag.api.main:app --reload

# Access services
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Admin Dashboard: http://localhost:8000/api/admin/dashboard
```

## Tech Stack

- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 17 + pgvector
- **ORM**: SQLModel (SQLAlchemy 2.0 + Pydantic)
- **RAG**: LangChain, FAISS/Qdrant
- **LLMs**: OpenAI, Anthropic, AWS Bedrock, Azure OpenAI
- **Embeddings**: HuggingFace Sentence Transformers
- **ETL**: Custom pipeline with Airflow (dev only)
- **Cloud**: AWS S3, Azure Blob Storage
- **Testing**: pytest, pytest-cov
- **Code Quality**: Ruff (format + lint), MyPy

## Project Structure

```
backend/
├── green_gov_rag/              # Main package
│   ├── api/                    # FastAPI application
│   │   ├── admin/              # Admin endpoints
│   │   ├── routes/             # Public API routes
│   │   ├── services/           # Business logic
│   │   │   ├── analytics_service.py
│   │   │   ├── cache_service.py
│   │   │   └── trust_score_service.py
│   │   ├── schemas/            # Pydantic models
│   │   └── main.py             # FastAPI app
│   ├── models/                 # SQLModel database models
│   │   ├── document.py
│   │   ├── chunk.py
│   │   └── query_log.py
│   ├── rag/                    # RAG components
│   │   ├── embeddings.py       # Embedding models
│   │   ├── llm_factory.py      # Multi-provider LLM support
│   │   ├── vector_store.py     # Vector store abstraction
│   │   ├── hybrid_search.py    # BM25 + vector hybrid search
│   │   ├── enhanced_response.py # Response generation
│   │   ├── location_ner.py     # Location NER for Australia
│   │   └── stores/             # FAISS & Qdrant implementations
│   ├── etl/                    # ETL pipeline
│   │   ├── pipeline.py         # Main pipeline orchestration
│   │   ├── ingest.py           # Document ingestion
│   │   ├── loader.py           # Document loading
│   │   ├── parsers/            # PDF, HTML, layout parsers
│   │   ├── chunker.py          # Text chunking strategies
│   │   ├── metadata_tagger.py  # LLM-powered metadata tagging
│   │   ├── db_writer.py        # Database operations
│   │   ├── storage_adapter.py  # Cloud storage abstraction
│   │   └── sources/            # Document source plugins
│   │       ├── base.py
│   │       ├── epbc_scraper.py
│   │       ├── sa_legislation.py
│   │       └── nsw_planning.py
│   ├── cloud/                  # Cloud storage
│   │   └── storage.py          # AWS/Azure/Local backends
│   ├── airflow/                # Airflow DAGs (dev only)
│   │   └── dags/
│   ├── scripts/                # Utility scripts
│   ├── config.py               # Centralized configuration
│   └── cli.py                  # CLI commands
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   └── env.py
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── conftest.py             # Test fixtures
├── configs/                    # Configuration files
│   └── documents_config.yml    # Document source configuration
├── pyproject.toml              # Dependencies & tooling
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## Key Features

### 1. Multi-LLM Support

Configure your preferred LLM provider via environment variables:

```bash
# OpenAI (Recommended: gpt-4o-mini)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Azure OpenAI (Best cost/performance)
LLM_PROVIDER=azure
LLM_MODEL=gpt-4o-mini
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://....openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini

# AWS Bedrock
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=...
```

### 2. Vector Store Options

```bash
# FAISS (Local, development)
VECTOR_STORE_TYPE=faiss
FAISS_INDEX_PATH=./data/vectors/faiss_index

# Qdrant (Production)
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key  # Optional
```

### 3. Cloud Storage

```bash
# Local filesystem (development)
CLOUD_PROVIDER=local
LOCAL_STORAGE_PATH=./data/storage

# AWS S3
CLOUD_PROVIDER=aws
STORAGE_CONTAINER=greengovrag-documents
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Azure Blob Storage
CLOUD_PROVIDER=azure
STORAGE_CONTAINER=greengovrag-documents
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
```

### 4. RAG Pipeline

- **Hybrid Search**: BM25 + Vector similarity
- **Geospatial Filtering**: Filter by Local Government Area (LGA)
- **Trust Scoring**: Confidence scores for responses
- **Citation Verification**: Track and verify source citations
- **Metadata Enrichment**: Auto-tagging with LLMs

### 5. ETL Pipeline

- **Multi-source**: Federal, State, Local government documents
- **Auto-tagging**: LLM-powered metadata extraction
- **Chunking**: Semantic and hierarchical chunking
- **Cloud Integration**: Store documents in S3/Azure/Local
- **Incremental Updates**: Only process new/changed documents

## Installation

### Using pip

```bash
# Base installation
pip install -e .

# Development (includes test tools, linters)
pip install -e .[dev]

# AWS support
pip install -e .[aws]

# Azure support
pip install -e .[azure]

# All extras
pip install -e .[dev,aws,azure]
```

### Using Docker

See [deploy/README.md](../deploy/README.md) for Docker setup.

## Configuration

All settings in `green_gov_rag/config.py`, loaded from `.env` file:

### Required Settings

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/greengovrag

# LLM Provider (choose one)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Vector Store
VECTOR_STORE_TYPE=faiss
```

### Optional Settings

```bash
# RAG Parameters
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
ENABLE_HYBRID_SEARCH=true

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Rate Limiting
API_RATE_LIMIT=30/minute

# Caching
ENABLE_CACHE=true
CACHE_TTL=3600

# Cloud Storage
CLOUD_PROVIDER=local
STORAGE_CONTAINER=greengovrag-documents

# Debug
DEBUG=false
LOG_LEVEL=INFO
```

See `.env.example` for complete list.

## Development

### Code Quality

```bash
# Format code (Ruff)
ruff format .

# Lint
ruff check .

# Type check (MyPy)
mypy green_gov_rag tests

# Run all checks
make format lint mypy
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest --cov=green_gov_rag tests/

# Specific test markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m "not slow"    # Skip slow tests

# Verbose output
pytest -v tests/
```

## API Endpoints

### Public API (`/api/*`)

```
GET  /api/health                 # Health check
POST /api/query                  # RAG query
  {
    "query": "Do I need an EIA?",
    "lga_name": "Dubbo Regional",  # Optional
    "top_k": 5                     # Optional
  }
GET  /api/documents              # List documents
GET  /api/analytics              # Analytics stats
GET  /api/lga-boundaries         # LGA GeoJSON data
```

### Admin API (`/api/admin/*`)

```
GET    /api/admin/dashboard              # Dashboard stats
GET    /api/admin/documents              # List all documents
GET    /api/admin/documents/{id}         # Document details
POST   /api/admin/documents/{id}/reprocess  # Reprocess document
DELETE /api/admin/documents/{id}         # Delete document
GET    /api/admin/analytics/queries      # Query analytics
GET    /api/admin/system/health          # System health
```

## Common Tasks

### 1. Run ETL Pipeline

```bash
# Using CLI
greengovrag-cli etl run-pipeline --config configs/documents_config.yml

# Using Docker
docker-compose exec backend greengovrag-cli etl run-pipeline

# Via GitHub Actions (production)
# Scheduled daily at 2 AM UTC
# Or manual trigger: Actions → ETL Pipeline - Scheduled → Run workflow
```

### 2. Query the RAG System

```bash
# Using CLI
greengovrag-cli rag query --query "Can I clear native vegetation?"

# Using API
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Do I need an EIA for a solar farm?", "lga_name": "Dubbo Regional"}'

# Using Python
from green_gov_rag.rag import query_rag

result = query_rag(
    query="What are the emissions reporting requirements?",
    lga_name="Adelaide",
    top_k=5
)
print(result['answer'])
```

### 3. Add a New Document Source

```python
# Create: green_gov_rag/etl/sources/my_source.py
from green_gov_rag.etl.sources.base import BaseDocumentSource
from langchain.schema import Document

class MySourceScraper(BaseDocumentSource):
    """Scraper for My Source documents."""

    def fetch_documents(self) -> list[Document]:
        """Fetch documents from source."""
        # Implement fetching logic
        documents = []
        # ... scraping logic ...
        return documents

    def validate_config(self) -> None:
        """Validate configuration."""
        required = ['url', 'jurisdiction']
        for field in required:
            if field not in self.config:
                raise ValueError(f"Missing required field: {field}")
```

Register in `configs/documents_config.yml`:

```yaml
sources:
  - type: my_source
    enabled: true
    name: "My Source Documents"
    config:
      url: https://example.gov.au
      jurisdiction: federal
      category: environment
      topic: climate
```

### 4. Switch Vector Stores

```bash
# Update .env
VECTOR_STORE_TYPE=qdrant

# Migrate existing data
python -m green_gov_rag.scripts.migrate_vector_store \
  --from-type faiss \
  --to-type qdrant
```

## Testing

### Test Structure

```
tests/
├── unit/                  # Fast, mocked tests
│   ├── test_rag.py
│   ├── test_etl.py
│   └── test_api.py
├── integration/           # Real DB/services tests
│   ├── test_pipeline.py
│   └── test_vector_store.py
└── conftest.py           # Shared fixtures
```

### Writing Tests

```python
# tests/unit/test_my_feature.py
import pytest

def test_my_feature():
    """Test description."""
    # Arrange
    input_data = "test"

    # Act
    result = my_function(input_data)

    # Assert
    assert result == "expected"

@pytest.mark.integration
def test_with_database(db_session):
    """Integration test with database."""
    # Test with real database
    pass
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/api/health

# System health (admin)
curl http://localhost:8000/api/admin/system/health
```

### Logs

```bash
# Local
tail -f logs/greengovrag.log

# Docker
docker-compose logs -f backend

# AWS ECS
aws logs tail /ecs/greengovrag-backend --follow
```

### Metrics

- Query latency
- Cache hit rate
- LLM token usage
- Document coverage by jurisdiction
- Trust score distribution

## Deployment

### Local (Docker Compose)

```bash
cd deploy/docker
docker-compose up -d
```

### AWS (ECS Fargate)

```bash
cd deploy/aws
cdk deploy
```

### Azure (Container Apps)

```bash
cd deploy/azure
az deployment group create --template-file main.bicep
```

See [deploy/README.md](../deploy/README.md) for detailed deployment guide.

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
psql -U postgres -h localhost -c "SELECT version();"

# Test connection
python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://postgres:postgres@localhost:5432/greengovrag'); print('OK')"
```

### Vector Store Issues

```bash
# FAISS index not found
greengovrag-cli etl run-pipeline  # Rebuild index

# Qdrant connection timeout
curl http://localhost:6333/health
docker ps | grep qdrant
```

### LLM API Issues

```bash
# Rate limit exceeded
# Use gpt-4o-mini or reduce API_RATE_LIMIT

# API key invalid
echo $OPENAI_API_KEY  # Verify key is set
```

### Import Errors

```bash
# Reinstall in editable mode
pip install -e .[dev]

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

## Documentation

- **Full Documentation**: https://sdp5.github.io/green-gov-rag/
- **API Reference**: [/docs](http://localhost:8000/docs) (when server running)
- **Developer Guide**: [../docs/docs_src/developer-guide](../docs/docs_src/developer-guide)
- **ETL Guide**: [green_gov_rag/etl/README.md](green_gov_rag/etl/README.md)
- **Testing Guide**: [tests/README.md](tests/README.md)

## Contributing

See [Contributor Guide](../docs/docs_src/contributor-guide/overview.md) for:
- Development setup
- Code style guidelines (Ruff, MyPy)
- Testing requirements
- Pull request process

## License

Copyright © 2025-2026 Sundeep Anand. See [LICENSE](../LICENSE) for details.

---

**Frontend**: [frontend/README.md](../frontend/README.md)
**Deployment**: [deploy/README.md](../deploy/README.md)
**Documentation**: https://sdp5.github.io/green-gov-rag/
**Support**: [GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)
