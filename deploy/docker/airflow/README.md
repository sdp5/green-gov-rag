# GreenGovRAG Airflow Setup

This directory contains Airflow DAGs for orchestrating the GreenGovRAG ETL pipeline.

## Overview

All DAGs use `greengovrag-cli` commands via BashOperator to ensure consistency between manual and automated runs. The DAGs are designed to work in Docker environments with all dependencies pre-installed.

## Available DAGs

### `greengovrag_etl_pipeline`
Complete ETL pipeline that runs daily at midnight:
1. **Ingest**: Download documents from configured sources
2. **Parse**: Extract text from PDFs using Unstructured.io
3. **Chunk**: Split documents into semantic chunks
4. **Load**: Save chunks to PostgreSQL database
5. **Index**: Build Qdrant vector store embeddings
6. **Query**: Test pipeline with sample query

**Schedule**: Daily (`@daily`)
**Tags**: `greengovrag`, `etl`, `docker`

## Running Airflow Locally

### Start Airflow

```bash
cd green-gov-rag/deploy/docker
docker compose -f docker-compose.airflow.yml up --build
```

**Access Points:**
- Airflow UI: http://localhost:8080 (Login: `admin / admin`)
- Qdrant UI: http://localhost:6333/dashboard
- PostgreSQL (app): localhost:5432

### Trigger DAG Manually

Via UI:
1. Navigate to http://localhost:8080
2. Find `greengovrag_etl_pipeline` in the DAG list
3. Click the play button to trigger

Via CLI:
```bash
docker compose exec airflow-webserver airflow dags trigger greengovrag_etl_pipeline
```

### View DAG Logs

```bash
docker compose exec airflow-webserver airflow tasks logs greengovrag_etl_pipeline ingest_documents <execution-date>
```

## Architecture

The Docker Compose setup includes:
- **postgres-airflow**: PostgreSQL database for Airflow metadata
- **postgres-app**: PostgreSQL database for GreenGovRAG application data (with pgvector extension)
- **qdrant**: Vector database for embeddings and similarity search (ports 6333, 6334)
- **airflow-webserver**: Airflow web UI and API (port 8080)
- **airflow-scheduler**: Airflow task scheduler

Both Airflow services have:
- `greengovrag-cli` installed and available in PATH
- Access to backend code, configs, and data directories
- Connection to PostgreSQL databases and Qdrant vector store

## DAG Configuration

All DAGs use paths relative to the Docker container:
- Config: `/app/configs/documents_config.yml`
- Data: `/app/data/`
- Chunks: `/app/data/chunks/`
- Vector Store: `/app/data/vector_store/`

These paths are mapped via Docker volumes in `docker-compose.airflow.yml`.

## Environment Variables

The following environment variables are configured in docker-compose.airflow.yml:

**Airflow Configuration:**
- `AIRFLOW__CORE__SQL_ALCHEMY_CONN`: Connection to Airflow metadata database
- `AIRFLOW__CORE__EXECUTOR`: LocalExecutor (runs tasks in separate processes)
- `AIRFLOW__CORE__LOAD_EXAMPLES`: false (no example DAGs)

**GreenGovRAG Configuration:**
- `DATABASE_URL`: postgresql://greengovrag:greengovrag@postgres-app:5432/greengovrag
- `VECTOR_STORE_TYPE`: qdrant
- `QDRANT_URL`: http://qdrant:6333

**Optional API Keys:**
Uncomment in docker-compose.airflow.yml or mount `.env` file:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- `AZURE_STORAGE_CONNECTION_STRING`

## Database Setup

### Initialize GreenGovRAG Database

The application database (`postgres-app`) needs to be initialized with tables before running DAGs:

```bash
# Run Alembic migrations
docker compose exec airflow-webserver alembic upgrade head

# Or initialize manually
docker compose exec airflow-webserver python -c "from green_gov_rag.models.base import init_db; init_db()"
```

### Verify Database Connection

```bash
# Check Airflow database
docker compose exec postgres-airflow psql -U airflow -d airflow -c "\dt"

# Check GreenGovRAG database
docker compose exec postgres-app psql -U greengovrag -d greengovrag -c "\dt"
```

## Development

### Adding New DAGs

1. Create a new Python file in `deploy/docker/airflow/dags/`
2. Use `greengovrag-cli` commands via BashOperator
3. Follow the pattern in `rag_pipeline_dag.py`
4. Restart Airflow to load new DAGs

### Testing DAGs

```bash
# Test a specific DAG
docker compose exec airflow-webserver airflow dags test greengovrag_etl_pipeline 2025-11-01

# List all DAGs
docker compose exec airflow-webserver airflow dags list

# Validate DAG structure
docker compose exec airflow-webserver airflow dags show greengovrag_etl_pipeline
```

## Troubleshooting

### DAG not appearing in UI
```bash
# Check for import errors
docker compose exec airflow-webserver airflow dags list-import-errors

# Restart scheduler
docker compose restart airflow-scheduler
```

### Task failures
```bash
# View task logs
docker compose logs airflow-webserver

# Check task instance
docker compose exec airflow-webserver airflow tasks state greengovrag_etl_pipeline ingest_documents <date>
```

### Reset Airflow database
```bash
docker compose down -v
docker compose up -d
```
