# Local Docker Deployment

> Quick setup for development and testing using Docker Compose

## Prerequisites

- Docker Desktop 4.0+ (or Docker Engine + Docker Compose)
- 8GB RAM minimum
- 20GB free disk space
- Git installed

## Quick Start (5 Minutes)

### 1. Clone Repository

```bash
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag
```

### 2. Configure Environment

```bash
cd deploy/docker
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Required: LLM API Key
OPENAI_API_KEY=sk-your-key-here

# Optional: Vector store (default: FAISS)
VECTOR_STORE_TYPE=faiss

# Optional: Database (defaults provided)
DATABASE_URL=postgresql://greengovrag:greengovrag@postgres:5432/greengovrag
```

### 3. Start Services

**Production mode** (backend + frontend + database):

```bash
docker-compose up
```

**Development mode** (includes Airflow UI):

```bash
docker-compose --profile dev up
```

### 4. Verify Services

**Backend API**:
```bash
curl http://localhost:8000/api/health
```

**Frontend**: Open http://localhost:3000

**Airflow UI** (dev mode): Open http://localhost:8080
- Username: `admin`
- Password: `admin`

### 5. Run ETL Pipeline

**Using Airflow UI** (dev mode):
1. Open http://localhost:8080
2. Enable `greengovrag_full_pipeline` DAG
3. Click "Trigger DAG"

**Using CLI**:
```bash
docker-compose exec backend greengovrag-cli etl run-pipeline
```

### 6. Query RAG System

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the NGER reporting requirements?",
    "max_sources": 5
  }'
```

## Architecture

### Docker Compose Services

```yaml
services:
  postgres:       # PostgreSQL database
  backend:        # FastAPI application
  frontend:       # React application
  airflow-webserver:   # Airflow UI (dev only)
  airflow-scheduler:   # Airflow scheduler (dev only)
  redis:          # Airflow backend (dev only)
```

### Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| Frontend | 3000 | http://localhost:3000 |
| PostgreSQL | 5432 | localhost:5432 |
| Airflow UI | 8080 | http://localhost:8080 |
| Redis | 6379 | localhost:6379 |

### Volumes

- `postgres_data`: Database persistence
- `vector_data`: FAISS vector index
- `raw_documents`: Downloaded PDFs
- `processed_data`: Processed chunks
- `airflow_logs`: Airflow logs (dev mode)

## Configuration Options

### Vector Store Selection

**FAISS (Default - In-Memory)**:
```bash
# In .env
VECTOR_STORE_TYPE=faiss
```

**Qdrant (Production-like)**:
```bash
# Add to docker-compose.yml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
  volumes:
    - qdrant_data:/qdrant/storage

# In .env
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://qdrant:6333
```

### LLM Provider Selection

**OpenAI (Default)**:
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
OPENAI_API_KEY=sk-...
```

**Azure OpenAI**:
```bash
LLM_PROVIDER=azure
LLM_MODEL=gpt-5-mini
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
```

**AWS Bedrock**:
```bash
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

### Database Configuration

**PostgreSQL (Default)**:
```bash
DATABASE_URL=postgresql://greengovrag:greengovrag@postgres:5432/greengovrag
```

**External PostgreSQL**:
```bash
# Remove postgres service from docker-compose.yml
DATABASE_URL=postgresql://user:pass@external-host:5432/dbname
```

## Development Workflow

### Hot Reload

Backend has hot reload enabled by default:

```bash
# Edit files in backend/green_gov_rag/
# Changes auto-reload in container
```

### Running Tests

```bash
# Inside backend container
docker-compose exec backend pytest tests/

# With coverage
docker-compose exec backend pytest --cov=green_gov_rag tests/
```

### Accessing Database

```bash
# PostgreSQL shell
docker-compose exec postgres psql -U greengovrag -d greengovrag

# Run SQL query
docker-compose exec postgres psql -U greengovrag -d greengovrag \
  -c "SELECT COUNT(*) FROM documents;"
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Rebuilding Services

```bash
# Rebuild single service
docker-compose build backend

# Rebuild and restart
docker-compose up --build backend

# Clean rebuild (remove volumes)
docker-compose down -v
docker-compose up --build
```

## Troubleshooting

### Issue: Port Already in Use

**Error**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution**: Change port in `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Use port 8001 instead
```

### Issue: Database Connection Failed

**Error**: `FATAL: password authentication failed`

**Solution**: Reset database:

```bash
docker-compose down -v  # Remove volumes
docker-compose up postgres  # Recreate database
```

### Issue: Out of Memory

**Error**: Container crashes with OOM

**Solution**: Increase Docker memory:
- Docker Desktop: Settings → Resources → Memory (increase to 8GB+)
- Linux: Edit `/etc/docker/daemon.json`

### Issue: pgvector Extension Not Found

**Error**: `extension "vector" is not available`

**Solution**: Ensure init script runs:

```bash
docker-compose down -v
docker-compose up postgres
# Wait for "database system is ready to accept connections"
docker-compose up backend
```

### Issue: Airflow DAG Not Showing

**Solution**: Wait for DAG to load (30-60 seconds), then refresh:

```bash
# Force DAG refresh
docker-compose exec airflow-scheduler airflow dags list
```

### Issue: Vector Store Empty

**Error**: `No documents found in vector store`

**Solution**: Run ETL pipeline:

```bash
docker-compose exec backend greengovrag-cli etl run-pipeline
```

## Performance Optimization

### Use Qdrant Instead of FAISS

For better performance with large datasets:

1. Add Qdrant service to `docker-compose.yml`
2. Set `VECTOR_STORE_TYPE=qdrant`
3. Run ETL pipeline

### Limit Document Sources

For faster testing, limit sources in `backend/configs/documents_config.yml`:

```yaml
sources:
  - type: federal_legislation
    enabled: true  # Only enable a few sources
  - type: state_legislation
    enabled: false  # Disable others
```

### Reduce Chunk Size

For faster embedding generation:

```bash
# In .env
CHUNK_SIZE=300  # Reduce from 500
CHUNK_OVERLAP=50  # Reduce from 100
```

## Cleanup

### Stop Services

```bash
# Stop but keep data
docker-compose stop

# Stop and remove containers (keep volumes)
docker-compose down

# Stop and remove everything (including data)
docker-compose down -v
```

### Remove Unused Images

```bash
docker image prune -a
```

### Free Disk Space

```bash
# Remove all unused data
docker system prune -a --volumes
```

## Next Steps

- [Configuration Guide](../getting-started/configuration.md) - Detailed configuration options
- [First Query](../getting-started/first-query.md) - Run your first RAG query
- [AWS Deployment](aws.md) - Deploy to production
- [Monitoring](monitoring.md) - Set up monitoring and logging

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
