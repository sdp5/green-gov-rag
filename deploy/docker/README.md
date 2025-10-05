# Docker Deployment

Complete Docker setup for GreenGovRAG with all services.

## Services

- **PostgreSQL** (port 5432) - Database
- **Redis** (port 6379) - Caching
- **Backend** (port 8000) - FastAPI
- **Frontend** (port 3000/80) - React
- **Streamlit** (port 8501) - Legacy UI
- **Airflow** (port 8080) - Orchestration

## Quick Start

### Development

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up --build

# Or start specific services
docker-compose up postgres redis backend
```

### Production

```bash
# Copy and configure
cp .env.example .env
# Edit with production values

# Deploy
docker-compose -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Stop services
docker-compose -f docker-compose.prod.yml down
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React UI |
| Backend API | http://localhost:8000 | FastAPI |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Streamlit | http://localhost:8501 | Legacy UI |
| Airflow | http://localhost:8080 | Orchestration |
| PostgreSQL | localhost:5432 | Database |

## Database Initialization

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Or manually
docker-compose exec backend python -c "from green_gov_rag.models.base import init_db; init_db()"
```

## Troubleshooting

### Reset database
```bash
docker-compose down -v
docker-compose up -d postgres
docker-compose exec backend alembic upgrade head
```

### View logs
```bash
docker-compose logs -f [service_name]
```

### Rebuild specific service
```bash
docker-compose up -d --build backend
```
