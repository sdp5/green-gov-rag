# GreenGovRAG Backend

Python backend with FastAPI, RAG, ETL, and Airflow orchestration.

## Quick Start

```bash
# Install
pip install -e .[dev]

# Configure
cp .env.example .env
# Edit .env with your settings

# Initialize database
alembic upgrade head

# Run API server
uvicorn green_gov_rag.api.main:app --reload

# Access services
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Admin: http://localhost:8000/api/admin/dashboard
# - Airflow: http://localhost:8080

# Run tests
pytest tests/
```

## Structure

```
backend/
├── green_gov_rag/          # Main package
│   ├── api/                # FastAPI routes & services
│   ├── models/             # Database models (SQLModel)
│   ├── rag/                # RAG components (vector store, LLM, embeddings)
│   ├── etl/                # ETL pipeline (parsing, chunking, metadata)
│   ├── airflow/            # Airflow DAGs
│   ├── config.py           # Centralized configuration
│   └── scripts/            # Utility scripts
├── alembic/                # Database migrations
├── tests/                  # Test suite
├── configs/                # Document configs
└── pyproject.toml          # Dependencies & tooling
```

## Key Features

### Multi-Platform LLM Support
Configure via `.env`:
```bash
LLM_PROVIDER=openai  # or azure, bedrock, anthropic
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...
```

### Vector Store Options
```bash
VECTOR_STORE_TYPE=faiss  # or qdrant
QDRANT_URL=http://localhost:6333
```

### Cloud Storage
```bash
CLOUD_PROVIDER=local  # or aws, azure
AWS_ACCESS_KEY_ID=...
```

## Common Commands

```bash
# Development
make format          # Format code
make lint            # Run linters
make mypy            # Type check
make test            # Run tests

# Database
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# API
uvicorn green_gov_rag.api.main:app --reload --port 8000

# Airflow (optional)
airflow standalone
```

## Testing

```bash
# All tests (fast, mocked)
pytest tests/

# With coverage
pytest --cov=green_gov_rag tests/

# Integration tests (requires Docker)
cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..
pytest -m integration
```

## Configuration

All settings in `green_gov_rag/config.py`, loaded from `.env`:

- **LLM**: Provider, model, API keys
- **Embeddings**: Model selection
- **Vector Store**: Type, path, Qdrant URL
- **Database**: PostgreSQL connection
- **Cloud**: Provider, credentials, storage paths
- **RAG**: Chunk size, overlap, top-k results
- **API**: Host, port, CORS origins

## Documentation

- `tests/README.md` - Testing guide
- `green_gov_rag/etl/sources/README.md` - Document source plugins
- `configs/documents_config.yml` - Document configuration

## API Endpoints

### Public API
```
GET  /api/health                 # Health check
POST /api/query                  # RAG query
GET  /api/documents              # List documents
GET  /api/analytics              # Analytics stats
GET  /api/lga-boundaries         # LGA GeoJSON
```

### Admin API
```
GET    /api/admin/dashboard              # Dashboard statistics
GET    /api/admin/documents              # List documents with filters
GET    /api/admin/documents/{id}         # Document details
POST   /api/admin/documents/{id}/reprocess  # Trigger reprocessing
DELETE /api/admin/documents/{id}         # Delete document
GET    /api/admin/analytics/queries      # Query analytics (last N days)
GET    /api/admin/system/health          # System health check
```

## Development

```bash
# Install with dev dependencies
pip install -e .[dev]

# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy green_gov_rag tests

# Build package
python -m build
```
