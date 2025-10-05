# GreenGovRAG Backend

Python backend with FastAPI, RAG, ETL, and Airflow orchestration.

## Structure

```
backend/
├── green_gov_rag/          # Main Python package
│   ├── api/                # FastAPI routes
│   ├── models/             # SQLModel database models
│   ├── rag/                # RAG components
│   ├── etl/                # ETL pipeline
│   ├── airflow/            # Airflow DAGs
│   ├── app/                # Streamlit UI (legacy)
│   └── scripts/            # Utility scripts
├── alembic/                # Database migrations
├── tests/                  # Test suite
└── pyproject.toml          # Dependencies
```

## Setup

```bash
# Install dependencies
pip install -e .

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Initialize database
alembic upgrade head

# Run FastAPI server
uvicorn green_gov_rag.api.main:app --reload --port 8000

# Run Streamlit (optional)
streamlit run green_gov_rag/app/ui.py

# Run Airflow (optional)
airflow standalone
```

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Testing

```bash
make test
# or
pytest
```
