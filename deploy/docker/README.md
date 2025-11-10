# Docker Deployment

Docker setup for GreenGovRAG local development and testing.

**Note**: For production deployments, use AWS (ECS Fargate) or Azure (Container Apps). See `deploy/aws/` and `deploy/azure/` directories.

## Services

- **PostgreSQL** (port 5432) - Database with pgvector extension
- **Qdrant** (port 6333) - Vector database
- **Redis** (port 6379) - Caching
- **Backend** (port 8000) - FastAPI
- **Frontend** (port 3000/80) - React (WIP)
- **Airflow** (port 8080) - ETL Orchestration

## Quick Start

### Local Development

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker compose up --build

# Or start specific services
docker compose up postgres qdrant redis backend
```

### Airflow Only

For ETL pipeline orchestration with Airflow:

```bash
cd deploy/docker
docker compose -f docker-compose.airflow.yml up --build
```

See `airflow/README.md` for detailed Airflow documentation.

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Backend API | http://localhost:8000 | X-API-Key header required |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Qdrant UI | http://localhost:6333/dashboard | Vector database |
| PostgreSQL | localhost:5432 | greengovrag / greengovrag |
| Redis | localhost:6379 | No auth (dev only) |

**Airflow** (separate compose file):
- Airflow UI: http://localhost:8080 (admin / admin)
- See `airflow/README.md`

## Database Initialization

```bash
# Run migrations
docker compose exec backend alembic upgrade head

# Or manually
docker compose exec backend python -c "from green_gov_rag.models.base import init_db; init_db()"
```

## Production Deployment

**Docker Compose is NOT recommended for production.** Use cloud-native deployments:

### AWS Deployment
```bash
cd deploy/aws
cdk deploy
```
See `deploy/aws/README.md` for details.

### Azure Deployment
```bash
cd deploy/azure
az deployment group create --resource-group greengovrag-rg --template-file main.bicep
```
See `deploy/azure/README.md` for details.

## Troubleshooting

### Reset database
```bash
docker compose down -v
docker compose up -d postgres
docker compose exec backend alembic upgrade head
```

### View logs
```bash
docker compose logs -f [service_name]
```

### Rebuild specific service
```bash
docker compose up -d --build backend
```

### Check vector store
```bash
# Qdrant collections
curl http://localhost:6333/collections

# Qdrant health
curl http://localhost:6333/health
```
