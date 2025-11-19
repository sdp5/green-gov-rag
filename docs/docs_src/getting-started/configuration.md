# Configuration

> Complete guide to configuring GreenGovRAG

## Environment Variables

All configuration is managed through environment variables in the `.env` file.

### Core Settings

```bash
# Application
APP_ENV=development  # development, staging, production
LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/greengovrag
```

### Authentication

```bash
# API Access Key (required for all endpoints except /api/health)
API_ACCESS_KEY=your-secret-key-here

# Recommended: Generate a secure key
# python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### LLM Configuration

#### OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o  # or gpt-4o-mini for cost savings
LLM_TEMPERATURE=0.0
```

#### Azure OpenAI (Recommended)

```bash
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
LLM_MODEL=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
LLM_TEMPERATURE=0.0
```

#### AWS Bedrock

```bash
LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
LLM_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

#### Anthropic

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-sonnet-20241022
```

### Vector Store Configuration

#### FAISS (Local Development)

```bash
VECTOR_STORE_TYPE=faiss
FAISS_INDEX_PATH=./data/vectors/faiss_index
```

#### Qdrant (Production)

```bash
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional for production
QDRANT_COLLECTION_NAME=greengovrag
```

### Embedding Configuration

```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384  # Depends on model
```

### Cloud Storage (Optional)

#### AWS S3

```bash
CLOUD_PROVIDER=aws
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=greengovrag-documents
AWS_REGION=ap-southeast-2
```

#### Azure Blob Storage

```bash
CLOUD_PROVIDER=azure
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER=greengovrag-documents
```

### Caching Configuration

```bash
# Enable caching
ENABLE_CACHE=true
CACHE_TTL=3600  # 1 hour in seconds

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# DynamoDB (AWS production)
DYNAMODB_TABLE_NAME=greengovrag-cache
```

### ETL Configuration

```bash
# Chunking
CHUNK_SIZE=1000          # tokens per chunk
CHUNK_OVERLAP=200        # token overlap
CHUNK_BATCH_SIZE=100     # chunks per batch

# Metadata tagging
ENABLE_AUTO_TAGGING=true
TAGGING_MODEL=gpt-4o-mini  # Cheaper model for tagging
```

### API Configuration

```bash
# Rate limiting
API_RATE_LIMIT=30/minute

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## Configuration Profiles

### Development

```bash
APP_ENV=development
LOG_LEVEL=DEBUG
VECTOR_STORE_TYPE=faiss
CLOUD_PROVIDER=local
ENABLE_CACHE=false
```

### Production

```bash
APP_ENV=production
LOG_LEVEL=INFO
VECTOR_STORE_TYPE=qdrant
CLOUD_PROVIDER=aws
ENABLE_CACHE=true
API_RATE_LIMIT=100/minute
```

## Validation

All configuration is validated on startup using Pydantic. Invalid configuration will cause the application to fail fast with clear error messages.

## See Also

- [LLM Configuration Guide](../developer-guide/llm-config.md)
- [Vector Store Guide](../user-guide/vector-stores.md)
- [Cloud Storage Guide](../developer-guide/cloud-storage.md)
