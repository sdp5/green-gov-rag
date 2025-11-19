# Custom Embeddings

> Configure and customize embedding models for semantic search

## Overview

GreenGovRAG uses embedding models to convert text into dense vector representations for semantic search. The default model is `sentence-transformers/all-MiniLM-L6-v2`, but you can customize this to use different models or providers based on your requirements.

## Default Configuration

### Sentence Transformers (Default)

**File**: `backend/green_gov_rag/rag/embeddings.py`

```python
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)
```

**Specifications**:

- **Dimensions**: 384
- **Max Sequence Length**: 256 tokens
- **Performance**: ~14,200 documents/sec on CPU
- **Size**: 80MB
- **Best for**: General-purpose semantic search, development

## Environment Configuration

Set embedding model in `.env`:

```bash
# Default (Sentence Transformers)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Or use larger model for better accuracy
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# OpenAI embeddings
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Azure OpenAI embeddings
EMBEDDING_PROVIDER=azure
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# AWS Bedrock embeddings
EMBEDDING_PROVIDER=bedrock
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1
```

## Alternative Models

### 1. Larger Sentence Transformers Models

**all-mpnet-base-v2** (Higher Quality)

```python
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    model_kwargs={"device": "cpu"}
)
```

**Specifications**:

- **Dimensions**: 768
- **Max Sequence Length**: 384 tokens
- **Performance**: ~2,800 documents/sec on CPU
- **Size**: 420MB
- **Best for**: Production with higher accuracy requirements

### 2. OpenAI Embeddings

**text-embedding-3-small** (Recommended)

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)
```

**Specifications**:

- **Dimensions**: 1536
- **Max Sequence Length**: 8191 tokens
- **Cost**: $0.02 per 1M tokens
- **Performance**: ~3,000 documents/sec
- **Best for**: High-quality production deployments

**text-embedding-3-large** (Highest Quality)

```python
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)
```

**Specifications**:

- **Dimensions**: 3072
- **Cost**: $0.13 per 1M tokens
- **Best for**: Maximum accuracy requirements

### 3. Azure OpenAI Embeddings

```python
from langchain_openai import AzureOpenAIEmbeddings

embeddings = AzureOpenAIEmbeddings(
    azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
    openai_api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)
```

**Specifications**:

- Same as OpenAI models
- **Best for**: Enterprise Azure deployments

### 4. AWS Bedrock Embeddings

```python
from langchain_community.embeddings import BedrockEmbeddings

embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v1",
    region_name=os.getenv("AWS_REGION", "us-east-1")
)
```

**Specifications**:

- **Dimensions**: 1536
- **Max Sequence Length**: 8192 tokens
- **Cost**: $0.0001 per 1K tokens
- **Best for**: AWS-native deployments

### 5. Cohere Embeddings

```python
from langchain_community.embeddings import CohereEmbeddings

embeddings = CohereEmbeddings(
    model="embed-english-v3.0",
    cohere_api_key=os.getenv("COHERE_API_KEY")
)
```

**Specifications**:

- **Dimensions**: 1024
- **Max Sequence Length**: 512 tokens
- **Cost**: $0.10 per 1M tokens
- **Best for**: Multilingual or specialized domains

## Implementation Guide

### Step 1: Update Configuration

**Edit** `backend/green_gov_rag/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Embedding Configuration
    embedding_provider: str = "sentence-transformers"  # sentence-transformers, openai, azure, bedrock
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384  # Update based on model

    # Provider-specific settings
    openai_embedding_model: str = "text-embedding-3-small"
    azure_openai_embedding_deployment: str = ""
    bedrock_embedding_model: str = "amazon.titan-embed-text-v1"

    class Config:
        env_file = ".env"
```

### Step 2: Create Embedding Factory

**Create** `backend/green_gov_rag/rag/embedding_factory.py`:

```python
"""Embedding model factory for multi-provider support."""
import os
from typing import Any
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
from langchain_community.embeddings import BedrockEmbeddings, CohereEmbeddings
from green_gov_rag.config import settings

def get_embeddings(provider: str | None = None) -> Embeddings:
    """Get embedding model based on provider.

    Args:
        provider: Embedding provider (sentence-transformers, openai, azure, bedrock, cohere)

    Returns:
        Embeddings instance

    Raises:
        ValueError: If provider is not supported
    """
    provider = provider or settings.embedding_provider

    if provider == "sentence-transformers":
        return HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

    elif provider == "openai":
        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

    elif provider == "azure":
        return AzureOpenAIEmbeddings(
            azure_deployment=settings.azure_openai_embedding_deployment,
            openai_api_version="2023-05-15",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY")
        )

    elif provider == "bedrock":
        return BedrockEmbeddings(
            model_id=settings.bedrock_embedding_model,
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

    elif provider == "cohere":
        return CohereEmbeddings(
            model="embed-english-v3.0",
            cohere_api_key=os.getenv("COHERE_API_KEY")
        )

    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
```

### Step 3: Update Vector Store Initialization

**Edit** `backend/green_gov_rag/rag/vector_store.py`:

```python
from green_gov_rag.rag.embedding_factory import get_embeddings

# Replace hardcoded embeddings with factory
embeddings = get_embeddings()

# Initialize vector store
vector_store = FAISS.from_documents(
    documents=chunks,
    embedding=embeddings
)
```

### Step 4: Migrate Existing Vectors

If changing embedding models, you must re-embed all documents:

```bash
# Backup existing vector store
cp -r data/vectors data/vectors.backup

# Re-run ETL pipeline with new embeddings
greengovrag-cli etl run-pipeline --force-reindex
```

## Performance Comparison

| Model | Dimensions | Speed (docs/sec) | Quality | Cost | Best For |
|-------|-----------|------------------|---------|------|----------|
| all-MiniLM-L6-v2 | 384 | 14,200 | Good | Free | Development, prototyping |
| all-mpnet-base-v2 | 768 | 2,800 | Better | Free | Production (local) |
| text-embedding-3-small | 1536 | 3,000 | Excellent | $0.02/1M | Production (API) |
| text-embedding-3-large | 3072 | 1,500 | Best | $0.13/1M | Maximum accuracy |
| amazon.titan-embed-text-v1 | 1536 | 2,500 | Excellent | $0.0001/1K | AWS deployments |

## Optimization Techniques

### 1. Batch Processing

Process documents in batches to improve throughput:

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

# Process in batches of 100
batch_size = 100
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    embeddings_batch = embeddings.embed_documents([c.page_content for c in batch])
    # Store embeddings_batch
```

### 2. Caching Embeddings

Cache embeddings to avoid recomputation:

```python
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore

store = LocalFileStore("./data/embedding_cache/")
cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings=embeddings,
    document_embedding_cache=store,
    namespace="greengovrag"
)
```

### 3. Dimensionality Reduction

Reduce embedding dimensions for faster search:

```python
from sklearn.decomposition import PCA
import numpy as np

# Reduce from 1536 to 384 dimensions
pca = PCA(n_components=384)
reduced_embeddings = pca.fit_transform(embeddings_matrix)

# Trade-off: ~70% faster search, ~5-10% quality loss
```

### 4. GPU Acceleration

Use GPU for faster embedding generation:

```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    model_kwargs={"device": "cuda"},  # Use GPU
    encode_kwargs={"normalize_embeddings": True, "batch_size": 32}
)
```

## Testing Embedding Quality

### Similarity Search Test

```python
from green_gov_rag.rag.embedding_factory import get_embeddings
from langchain_community.vectorstores import FAISS

embeddings = get_embeddings()
vector_store = FAISS.load_local("data/vectors", embeddings)

# Test query
query = "What are the NGER reporting requirements for Scope 2 emissions?"
results = vector_store.similarity_search_with_score(query, k=5)

for doc, score in results:
    print(f"Score: {score:.4f}")
    print(f"Content: {doc.page_content[:200]}")
    print("---")
```

### A/B Testing Different Models

```python
import time

models = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-mpnet-base-v2"
]

for model_name in models:
    embeddings = HuggingFaceEmbeddings(model_name=model_name)

    start = time.time()
    results = vector_store.similarity_search(query, k=5)
    elapsed = time.time() - start

    print(f"{model_name}: {elapsed:.4f}s, Top result: {results[0].metadata['title']}")
```

## Troubleshooting

### Issue: Out of Memory

**Solution**: Reduce batch size or use smaller model

```python
# In config.py
embedding_batch_size: int = 32  # Reduce from 100
```

### Issue: Slow Embedding Generation

**Solution**: Use GPU or switch to API-based embeddings

```bash
# In .env
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Issue: Poor Search Quality

**Solution**: Use larger embedding model or tune chunking

```bash
# In .env
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# Or adjust chunking in config.py
CHUNK_SIZE=500  # Increase from 300
CHUNK_OVERLAP=100  # Increase from 50
```

### Issue: Dimension Mismatch

**Error**: `RuntimeError: mat1 and mat2 shapes cannot be multiplied`

**Solution**: Delete vector store and re-index with correct dimensions

```bash
rm -rf data/vectors
greengovrag-cli etl run-pipeline --force-reindex
```

## Cost Optimization

### Development Strategy

Use free local models for development:

```bash
# .env.development
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Production Strategy

Use API-based models for production quality:

```bash
# .env.production
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Cost Estimation

For 10,000 regulatory documents (~500 tokens each):

| Provider | Model | Cost |
|----------|-------|------|
| Sentence Transformers | all-MiniLM-L6-v2 | $0 |
| OpenAI | text-embedding-3-small | $0.10 |
| OpenAI | text-embedding-3-large | $0.65 |
| AWS Bedrock | titan-embed-text-v1 | $0.50 |

## References

- [Sentence Transformers Documentation](https://www.sbert.net/)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [AWS Bedrock Embeddings](https://docs.aws.amazon.com/bedrock/latest/userguide/embeddings.html)
- [LangChain Embeddings](https://python.langchain.com/docs/modules/data_connection/text_embedding/)

---

**Last Updated**: 2025-11-22
