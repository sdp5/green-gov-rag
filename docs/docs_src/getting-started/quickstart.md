# Quick Start

> Get GreenGovRAG running in 5 minutes

## Prerequisites

- Docker and Docker Compose installed
- 4GB RAM available
- Internet connection for downloading images

## Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag

# Copy environment file
cp backend/.env.example backend/.env
```

## Step 2: Configure API Keys

Edit `backend/.env` and add your LLM API key:

```bash
# For OpenAI
OPENAI_API_KEY=sk-...

# Or for Azure OpenAI (recommended)
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
LLM_MODEL=gpt-4o

# Generate API access key for authentication
API_ACCESS_KEY=your-secret-key-here
```

## Step 3: Start Services

```bash
cd deploy/docker
docker-compose up
```

This starts:
- Backend API (port 8000)
- PostgreSQL database with pgvector
- Qdrant vector store (port 6333)

## Step 4: Submit Your First Query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{
    "query": "What are the emissions reporting requirements for facilities in NSW?",
    "max_sources": 5
  }'
```

## Step 5: Explore the API

Visit the interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## What's Next?

- [Run the ETL pipeline](../user-guide/document-sources.md) to ingest regulatory documents
- [Configure vector stores](../user-guide/vector-stores.md) for optimal performance
- [Deploy to production](../deployment/overview.md)

## Troubleshooting

**Container won't start?**
- Ensure ports 8000, 5432, and 6333 are available
- Check Docker has sufficient memory (4GB minimum)

**API key errors?**
- Verify your LLM provider API key is valid
- Ensure API_ACCESS_KEY is set and matches your request header
