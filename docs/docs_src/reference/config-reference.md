# Configuration Reference

> Complete reference for all configuration options

## Environment Variables

All configuration is managed through environment variables loaded from `.env` file.

### Core Settings

#### `ENVIRONMENT`
- **Type**: `str`
- **Default**: `development`
- **Options**: `development`, `staging`, `production`
- **Description**: Application environment mode

```bash
ENVIRONMENT=production
```

#### `LOG_LEVEL`
- **Type**: `str`
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Logging verbosity level

```bash
LOG_LEVEL=INFO
```

#### `API_RATE_LIMIT`
- **Type**: `str`
- **Default**: `30/minute`
- **Format**: `{count}/{time_unit}`
- **Description**: Rate limiting for API endpoints

```bash
API_RATE_LIMIT=100/minute
```

### LLM Configuration

#### `LLM_PROVIDER`
- **Type**: `str`
- **Default**: `openai`
- **Options**: `openai`, `azure`, `bedrock`, `anthropic`
- **Description**: LLM service provider

```bash
LLM_PROVIDER=openai
```

#### `LLM_MODEL`
- **Type**: `str`
- **Default**: `gpt-5-mini`
- **Options**: Provider-specific model names
- **Description**: LLM model to use for generation

**OpenAI Models**:
```bash
LLM_MODEL=gpt-5-mini              # Recommended: Fast, cheap
LLM_MODEL=gpt-5                   # Higher quality
LLM_MODEL=gpt-4o                  # Best quality, expensive
```

**Azure OpenAI Models**:
```bash
LLM_MODEL=gpt-5-mini              # Deployment name
```

**AWS Bedrock Models**:
```bash
LLM_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
LLM_MODEL=anthropic.claude-3-haiku-20240307-v1:0
LLM_MODEL=amazon.titan-text-express-v1
```

#### `LLM_TEMPERATURE`
- **Type**: `float`
- **Default**: `0.2`
- **Range**: `0.0` - `2.0`
- **Description**: Response randomness (lower = more deterministic)

```bash
LLM_TEMPERATURE=0.2
```

#### `LLM_MAX_TOKENS`
- **Type**: `int`
- **Default**: `4000`
- **Description**: Maximum tokens in LLM response

```bash
LLM_MAX_TOKENS=4000
```

### OpenAI Settings

#### `OPENAI_API_KEY`
- **Type**: `str`
- **Required**: Yes (if `LLM_PROVIDER=openai`)
- **Description**: OpenAI API key

```bash
OPENAI_API_KEY=sk-proj-...
```

#### `OPENAI_ORG_ID`
- **Type**: `str`
- **Optional**: Yes
- **Description**: OpenAI organization ID

```bash
OPENAI_ORG_ID=org-...
```

### Azure OpenAI Settings

#### `AZURE_OPENAI_ENDPOINT`
- **Type**: `str`
- **Required**: Yes (if `LLM_PROVIDER=azure`)
- **Format**: `https://{resource-name}.openai.azure.com`
- **Description**: Azure OpenAI endpoint URL

```bash
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com
```

#### `AZURE_OPENAI_API_KEY`
- **Type**: `str`
- **Required**: Yes (if `LLM_PROVIDER=azure`)
- **Description**: Azure OpenAI API key

```bash
AZURE_OPENAI_API_KEY=abc123...
```

#### `AZURE_OPENAI_DEPLOYMENT`
- **Type**: `str`
- **Required**: Yes (if `LLM_PROVIDER=azure`)
- **Description**: Deployment name for the model

```bash
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
```

#### `AZURE_OPENAI_API_VERSION`
- **Type**: `str`
- **Default**: `2023-05-15`
- **Description**: Azure OpenAI API version

```bash
AZURE_OPENAI_API_VERSION=2023-05-15
```

### AWS Bedrock Settings

#### `AWS_REGION`
- **Type**: `str`
- **Default**: `us-east-1`
- **Description**: AWS region for Bedrock

```bash
AWS_REGION=us-east-1
```

#### `AWS_ACCESS_KEY_ID`
- **Type**: `str`
- **Required**: Yes (if `LLM_PROVIDER=bedrock`)
- **Description**: AWS access key ID

```bash
AWS_ACCESS_KEY_ID=AKIA...
```

#### `AWS_SECRET_ACCESS_KEY`
- **Type**: `str`
- **Required**: Yes (if `LLM_PROVIDER=bedrock`)
- **Description**: AWS secret access key

```bash
AWS_SECRET_ACCESS_KEY=...
```

### Anthropic Settings

#### `ANTHROPIC_API_KEY`
- **Type**: `str`
- **Required**: Yes (if `LLM_PROVIDER=anthropic`)
- **Description**: Anthropic API key

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### Vector Store Configuration

#### `VECTOR_STORE_TYPE`
- **Type**: `str`
- **Default**: `faiss`
- **Options**: `faiss`, `qdrant`
- **Description**: Vector store backend

```bash
VECTOR_STORE_TYPE=qdrant
```

#### `QDRANT_URL`
- **Type**: `str`
- **Default**: `http://localhost:6333`
- **Required**: Yes (if `VECTOR_STORE_TYPE=qdrant`)
- **Description**: Qdrant server URL

```bash
QDRANT_URL=http://qdrant:6333
```

#### `QDRANT_API_KEY`
- **Type**: `str`
- **Optional**: Yes
- **Description**: Qdrant API key (if authentication enabled)

```bash
QDRANT_API_KEY=...
```

#### `QDRANT_COLLECTION_NAME`
- **Type**: `str`
- **Default**: `greengovrag`
- **Description**: Qdrant collection name

```bash
QDRANT_COLLECTION_NAME=greengovrag
```

#### `FAISS_INDEX_PATH`
- **Type**: `str`
- **Default**: `data/vectors/faiss_index`
- **Description**: Path to FAISS index file

```bash
FAISS_INDEX_PATH=data/vectors/faiss_index
```

### Embedding Configuration

#### `EMBEDDING_MODEL`
- **Type**: `str`
- **Default**: `sentence-transformers/all-MiniLM-L6-v2`
- **Description**: Embedding model name

```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
```

#### `EMBEDDING_DIMENSIONS`
- **Type**: `int`
- **Default**: `384`
- **Description**: Embedding vector dimensions

```bash
EMBEDDING_DIMENSIONS=384
```

### Database Configuration

#### `DATABASE_URL`
- **Type**: `str`
- **Required**: Yes
- **Format**: `postgresql://{user}:{password}@{host}:{port}/{database}`
- **Description**: PostgreSQL connection string

```bash
DATABASE_URL=postgresql://greengovrag:password@localhost:5432/greengovrag
```

#### `DATABASE_POOL_SIZE`
- **Type**: `int`
- **Default**: `20`
- **Description**: Database connection pool size

```bash
DATABASE_POOL_SIZE=20
```

#### `DATABASE_MAX_OVERFLOW`
- **Type**: `int`
- **Default**: `10`
- **Description**: Max overflow connections beyond pool size

```bash
DATABASE_MAX_OVERFLOW=10
```

### Cloud Storage Configuration

#### `CLOUD_PROVIDER`
- **Type**: `str`
- **Default**: `local`
- **Options**: `local`, `aws`, `azure`
- **Description**: Cloud storage provider

```bash
CLOUD_PROVIDER=aws
```

#### `AWS_S3_BUCKET`
- **Type**: `str`
- **Required**: Yes (if `CLOUD_PROVIDER=aws`)
- **Description**: S3 bucket name for document storage

```bash
AWS_S3_BUCKET=greengovrag-documents
```

#### `AZURE_STORAGE_CONNECTION_STRING`
- **Type**: `str`
- **Required**: Yes (if `CLOUD_PROVIDER=azure`)
- **Description**: Azure Blob Storage connection string

```bash
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
```

#### `AZURE_STORAGE_CONTAINER`
- **Type**: `str`
- **Default**: `greengovrag`
- **Description**: Azure Blob Storage container name

```bash
AZURE_STORAGE_CONTAINER=greengovrag
```

### Caching Configuration

#### `CACHE_ENABLED`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Enable query result caching

```bash
CACHE_ENABLED=true
```

#### `CACHE_TTL_SECONDS`
- **Type**: `int`
- **Default**: `3600`
- **Description**: Cache time-to-live in seconds

```bash
CACHE_TTL_SECONDS=3600
```

#### `REDIS_URL`
- **Type**: `str`
- **Optional**: Yes
- **Format**: `redis://{host}:{port}/{db}`
- **Description**: Redis connection string for caching

```bash
REDIS_URL=redis://localhost:6379/0
```

### ETL Pipeline Configuration

#### `CHUNK_SIZE`
- **Type**: `int`
- **Default**: `500`
- **Description**: Text chunk size in tokens

```bash
CHUNK_SIZE=500
```

#### `CHUNK_OVERLAP`
- **Type**: `int`
- **Default**: `100`
- **Description**: Overlap between chunks in tokens

```bash
CHUNK_OVERLAP=100
```

#### `CHUNK_BATCH_SIZE`
- **Type**: `int`
- **Default**: `100`
- **Description**: Number of chunks to process in parallel

```bash
CHUNK_BATCH_SIZE=100
```

#### `DOCUMENTS_CONFIG_PATH`
- **Type**: `str`
- **Default**: `configs/documents_config.yml`
- **Description**: Path to document sources configuration

```bash
DOCUMENTS_CONFIG_PATH=configs/documents_config.yml
```

#### `RAW_DATA_DIR`
- **Type**: `str`
- **Default**: `data/raw`
- **Description**: Directory for downloaded documents

```bash
RAW_DATA_DIR=data/raw
```

#### `PROCESSED_DATA_DIR`
- **Type**: `str`
- **Default**: `data/processed`
- **Description**: Directory for processed chunks

```bash
PROCESSED_DATA_DIR=data/processed
```

### RAG Configuration

#### `TOP_K_RESULTS`
- **Type**: `int`
- **Default**: `5`
- **Description**: Number of documents to retrieve

```bash
TOP_K_RESULTS=5
```

#### `MIN_RELEVANCE_SCORE`
- **Type**: `float`
- **Default**: `0.3`
- **Range**: `0.0` - `1.0`
- **Description**: Minimum relevance score to include document

```bash
MIN_RELEVANCE_SCORE=0.3
```

#### `ENABLE_HYBRID_SEARCH`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Enable BM25 + vector hybrid search

```bash
ENABLE_HYBRID_SEARCH=true
```

#### `BM25_WEIGHT`
- **Type**: `float`
- **Default**: `0.3`
- **Range**: `0.0` - `1.0`
- **Description**: Weight for BM25 score in hybrid search

```bash
BM25_WEIGHT=0.3
```

### CORS Configuration

#### `CORS_ORIGINS`
- **Type**: `list[str]`
- **Default**: `["http://localhost:3000"]`
- **Format**: Comma-separated URLs
- **Description**: Allowed CORS origins

```bash
CORS_ORIGINS=http://localhost:3000,https://app.greengovrag.com
```

#### `CORS_ALLOW_CREDENTIALS`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Allow credentials in CORS requests

```bash
CORS_ALLOW_CREDENTIALS=true
```

## Configuration Profiles

### Development Profile

```bash
# .env.development
ENVIRONMENT=development
LOG_LEVEL=DEBUG
VECTOR_STORE_TYPE=faiss
DATABASE_URL=postgresql://greengovrag:greengovrag@localhost:5432/greengovrag
CLOUD_PROVIDER=local
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
CACHE_ENABLED=false
```

### Production Profile

```bash
# .env.production
ENVIRONMENT=production
LOG_LEVEL=INFO
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://qdrant:6333
DATABASE_URL=postgresql://greengovrag:${DB_PASSWORD}@rds-endpoint:5432/greengovrag
CLOUD_PROVIDER=aws
AWS_S3_BUCKET=greengovrag-prod-documents
LLM_PROVIDER=azure
LLM_MODEL=gpt-5-mini
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
```

## Configuration Loading

Configuration is loaded in this order (later sources override earlier):

1. **Default values** in `backend/green_gov_rag/config.py`
2. **Environment variables** from `.env` file
3. **System environment variables** (highest priority)

**Example**:
```python
from green_gov_rag.config import settings

# Access configuration
print(settings.llm_provider)  # 'openai'
print(settings.llm_model)      # 'gpt-5-mini'
```

## Validation

Configuration is validated on startup using Pydantic:

```python
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    llm_provider: str = "openai"

    @validator("llm_provider")
    def validate_provider(cls, v):
        allowed = ["openai", "azure", "bedrock", "anthropic"]
        if v not in allowed:
            raise ValueError(f"LLM provider must be one of {allowed}")
        return v
```

**Validation errors** will prevent the application from starting.

## Secrets Management

### Local Development

Use `.env` file (never commit to Git):

```bash
# .env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
```

### Production (AWS)

Use AWS Systems Manager Parameter Store:

```bash
aws ssm put-parameter \
  --name "/greengovrag/prod/openai-api-key" \
  --value "sk-..." \
  --type "SecureString"
```

### Production (Azure)

Use Azure Key Vault:

```bash
az keyvault secret set \
  --vault-name greengovrag-kv \
  --name openai-api-key \
  --value "sk-..."
```

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
