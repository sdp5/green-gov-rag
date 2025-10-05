# Project Structure

## Repository Layout

```
green-gov-rag/
├── backend/                # Python Backend
│   ├── green_gov_rag/
│   │   ├── api/           # FastAPI routes
│   │   ├── models/        # SQLModel ORM
│   │   ├── rag/           # RAG components
│   │   ├── etl/           # ETL pipeline + plugins
│   │   └── airflow/       # Airflow DAGs
│   ├── alembic/           # Database migrations
│   ├── tests/
│   ├── configs/           # YAML configs
│   └── pyproject.toml
│
├── frontend/              # React App
│   ├── src/
│   │   ├── pages/        # Query, Map, Analytics
│   │   ├── components/   # UI components
│   │   ├── api/          # API client
│   │   └── store/        # Zustand state
│   └── package.json
│
├── deploy/               # Deployment
│   ├── docker/          # Docker Compose
│   ├── aws/             # CDK for AWS
│   └── azure/           # Bicep for Azure
│
├── data/
│   ├── raw/             # Original PDFs/HTML
│   ├── processed/       # Chunked docs
│   └── geo/             # GeoJSON files
│
└── docs/                # Documentation
```

## Architecture

```
User Interface (React + Map)
           ↓
Query Handler (FastAPI/LangChain Agent)
           ↓
Document Retrieval (FAISS/Qdrant + Metadata)
           ↓
Document Chunk Store (Vector Index + PostgreSQL)
           ↓
ETL Pipeline (Airflow)
           ↓
Raw Data Sources (PDFs, HTML, GeoJSON)
```

## Components

### Data Engineering Layer

| Component | Description |
|-----------|-------------|
| ETL Pipeline | Airflow DAGs for download, parse, chunk, embed |
| Metadata Store | PostgreSQL with spatial metadata |
| Vector Store | FAISS/Qdrant for similarity search |
| Data Validation | Great Expectations (optional) |

**Supported File Types:**

| Type | Tools | Use Case |
|------|-------|----------|
| PDF | PyMuPDF, LLMSherpa, OCR | Policies, laws |
| HTML | BeautifulSoup, LangChain | Online pages |
| GeoJSON | GeoPandas, Folium | Map overlays |
| CSV/XLSX | Pandas | Tabular rules |

### Generative AI Layer

| Component | Description |
|-----------|-------------|
| Embedding Model | OpenAI/HuggingFace for vector embeddings |
| RAG Chain | LangChain retrieval + generation |
| Agent Tooling | LangChain AgentExecutor for intelligent routing |

### User Interface

| Component | Description |
|-----------|-------------|
| React App | Modern UI with Mapbox, charts, search |
| Mapbox Map | GeoJSON overlays, LGA filtering |
| Admin API | Document management, analytics dashboard |

### Deployment

| Component | Description |
|-----------|-------------|
| Docker | Containerized services |
| AWS/Azure | ECS Fargate or Container Apps |
| S3/Blob | Document and log storage |

## Data Flow

**1. Ingestion**
- Airflow downloads documents
- Parses, chunks with metadata
- Embeds to FAISS, logs to PostgreSQL

**2. User Query**
- User types query or clicks LGA on map
- Query + filters → RAG → LLM
- Results with citations

**3. Analytics (Optional)**
- Dashboards for LGA coverage, usage

## Program Flow

```
frontend/ (React UI)
    ↓
api/routes.py (FastAPI endpoints)
    ↓
rag/agent_tools.py (Agent wrapper)
    ↓
rag/rag_chain.py (RAG engine)
    ↓
    ├─ rag/vector_store.py (FAISS/Qdrant)
    └─ rag/embeddings.py (Embedding models)
        ↓
etl/chunker.py (Text splitters)
    ↓
etl/parsers/ (PDF/HTML dispatcher)
    ↓
etl/utils.py (Cleaning/normalizing)
```

## Key Features

| Feature | How It Helps |
|---------|--------------|
| RAG-based QA | Combines LLM reasoning with grounded sources |
| LGA Metadata Filtering | Location-based answer focusing |
| Interactive Map UI | Click LGA to filter queries |
| PostgreSQL/PostGIS | Advanced spatial joins |
| Automated ETL | Fresh, structured regulatory data |
| Agent-Driven | Chain tools via LangChain |

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React, Mapbox |
| Backend | FastAPI, LangChain |
| RAG | FAISS/Qdrant, OpenAI/Azure/Bedrock/Anthropic |
| ETL | Airflow, LLMSherpa, PyMuPDF |
| Database | PostgreSQL/PostGIS, SQLModel |
| Deployment | Docker, AWS ECS, Azure Container Apps |

## Quick Start

```bash
# Backend
cd backend
pip install -e .
alembic upgrade head
uvicorn green_gov_rag.api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker (all services)
cd deploy/docker
docker-compose up
```

## See Also

- [Overview](README.md) - System architecture
- [Cloud Deployment](./CLOUD_MIGRATION.md) - Multi-cloud setup
- [Data Sources](./DATA.md) - Document sources
- [Implementation](./IMPLEMENTATION_SUMMARY.md) - Migration details
