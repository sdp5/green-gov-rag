# Vector Store Migration Guide

## Overview

The GreenGovRAG application now supports multiple vector store backends through a factory pattern:
- **FAISS** - Fast, in-memory (development/small datasets)
- **Qdrant** - Production-grade, distributed (recommended for production)
- **ChromaDB** - Coming soon

## Quick Start

### Using the Factory

```python
from green_gov_rag.rag.vector_store_factory import create_vector_store
from green_gov_rag.rag.embeddings import ChunkEmbedder

# Initialize embeddings
embeddings = ChunkEmbedder().embedder

# Create vector store (uses config setting)
store = create_vector_store(embeddings)

# Or explicitly choose backend
store = create_vector_store(embeddings, store_type='qdrant')
```

### Configuration

Set in `.env`:

```bash
# Choose backend
VECTOR_STORE_TYPE=qdrant  # or 'faiss' or 'chromadb'

# FAISS settings (if using FAISS)
VECTOR_STORE_PATH=./data/vector_store

# Qdrant settings (if using Qdrant)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional for Qdrant Cloud
```

## Migrating from FAISS to Qdrant

### Step 1: Install Dependencies

```bash
pip install qdrant-client langchain-qdrant
```

### Step 2: Start Qdrant Server

**Option A: Docker (Recommended)**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

**Option B: Qdrant Cloud**
1. Sign up at https://qdrant.tech
2. Create a cluster
3. Get your API key and URL

### Step 3: Run Migration

```bash
# Dry run to see what would be migrated
python -m green_gov_rag.scripts.migrate_vector_store \
    --source faiss \
    --target qdrant \
    --dry-run

# Actual migration
python -m green_gov_rag.scripts.migrate_vector_store \
    --source faiss \
    --target qdrant \
    --source-path ./data/vector_store \
    --batch-size 1000
```

### Step 4: Update Configuration

```bash
# Update .env
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://localhost:6333
```

### Step 5: Restart Application

```bash
# Your app now uses Qdrant!
python -m green_gov_rag.cli rag query "What are emissions limits in NSW?"
```

## Comparison: FAISS vs Qdrant

| Feature | FAISS | Qdrant |
|---------|-------|--------|
| **Speed** | Very Fast (in-memory) | Fast (network overhead) |
| **Scalability** | Limited (memory bound) | High (distributed) |
| **Persistence** | File-based | Database-backed |
| **Metadata Filtering** | Post-filtering (slow) | Native (fast) |
| **CRUD Operations** | Add-only | Full CRUD |
| **Production Ready** | No | Yes |
| **Setup Complexity** | Easy (no server) | Medium (requires server) |
| **Cost** | Free | Free (self-hosted) or Paid (cloud) |
| **Best For** | Development, demos | Production, large datasets |

## Common Operations

### Check Available Backends

```python
from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

available = VectorStoreFactory.get_available_stores()
print(f"Available backends: {available}")
# Output: ['faiss', 'qdrant']
```

### Validate Configuration

```python
from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

# Validate current config
result = VectorStoreFactory.validate_config()
print(result)
# {
#   'valid': True,
#   'store_type': 'qdrant',
#   'issues': [],
#   'config': {'url': 'http://localhost:6333', ...}
# }

# Validate specific backend
result = VectorStoreFactory.validate_config('qdrant')
```

### Get Store Information

```python
store = create_vector_store(embeddings)

info = store.get_store_info()
print(info)
# {
#   'backend': 'qdrant',
#   'status': 'active',
#   'document_count': 15420,
#   'supports_deletion': True,
#   'supports_metadata_listing': True
# }
```

### Delete Documents (Qdrant only)

```python
# FAISS doesn't support deletion
# Use Qdrant for this feature

store = create_vector_store(embeddings, store_type='qdrant')
store.delete_by_id(['doc_123', 'doc_456'])
```

### List All Metadata (Qdrant only)

```python
store = create_vector_store(embeddings, store_type='qdrant')

# Get all metadata
metadata_list = store.list_metadata()
for meta in metadata_list[:5]:
    print(meta)
# {'region': 'NSW', 'topic': 'emissions', ...}
```

## Migration Troubleshooting

### Issue: "FAISS doesn't support metadata listing"

**Problem**: FAISS can't list all documents, only search.

**Solution**: Migration script uses broad similarity searches to extract documents. This may not capture all documents in very large datasets.

**Better approach**: Re-embed from source documents
```bash
# Instead of migrating, rebuild from scratch
VECTOR_STORE_TYPE=qdrant python -m green_gov_rag.scripts.build_embeddings
```

### Issue: "Qdrant connection failed"

**Problem**: Qdrant server not running.

**Solution**:
```bash
# Check if Qdrant is running
curl http://localhost:6333/collections

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Or check Qdrant Cloud URL/API key
```

### Issue: "Migration is slow"

**Problem**: Large dataset taking too long.

**Solutions**:
1. Increase batch size: `--batch-size 5000`
2. Use direct database migration (Qdrant → Qdrant)
3. Re-embed in parallel using Airflow DAG

### Issue: "Memory error during migration"

**Problem**: Too many documents loaded at once.

**Solution**: Reduce batch size
```bash
python -m green_gov_rag.scripts.migrate_vector_store \
    --batch-size 500  # Smaller batches
```

## Production Deployment

### Qdrant Production Setup

**1. Deploy Qdrant**

**Docker Compose:**
```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
```

**Kubernetes (Helm):**
```bash
helm repo add qdrant https://qdrant.to/helm
helm install qdrant qdrant/qdrant
```

**Qdrant Cloud:**
```bash
# Sign up: https://cloud.qdrant.io
# Create cluster
# Get URL and API key
```

**2. Configure Application**

```bash
# Production .env
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=https://your-cluster.qdrant.cloud
QDRANT_API_KEY=your-api-key-here
```

**3. Enable Features**

```python
# In production, Qdrant enables:
# - Metadata filtering (faster queries)
# - Document deletion (data management)
# - Scalability (millions of vectors)
# - Replication (high availability)
```

### Performance Tuning

**Qdrant Settings:**
```python
store = create_vector_store(
    embeddings,
    store_type='qdrant',
    url='http://localhost:6333',
    prefer_grpc=True,  # Faster than HTTP
    timeout=30,         # Increase for large datasets
)
```

**Indexing:**
```python
# Qdrant auto-creates indexes
# For custom indexing:
from qdrant_client import models

client.create_collection(
    collection_name="greengovrag",
    vectors_config=models.VectorParams(
        size=384,  # Embedding dimension
        distance=models.Distance.COSINE
    ),
    # Add HNSW index for speed
    hnsw_config=models.HnswConfigDiff(
        m=16,  # Links per node
        ef_construct=100
    )
)
```

## Rollback Plan

If migration fails or Qdrant has issues:

**1. Keep FAISS backup**
```bash
# Before migration, backup FAISS index
cp -r ./data/vector_store ./data/vector_store.backup
```

**2. Revert configuration**
```bash
# .env
VECTOR_STORE_TYPE=faiss
VECTOR_STORE_PATH=./data/vector_store.backup
```

**3. Restart application**
```bash
# App falls back to FAISS
uvicorn green_gov_rag.api.main:app
```

## Future: ChromaDB Support

ChromaDB support is planned. To add it:

1. Implement `ChromaVectorStore` class
2. Add to factory in `vector_store_factory.py`
3. Similar interface to Qdrant

Stay tuned for updates!

## Summary

✅ **Factory pattern**: Easy switching between backends
✅ **Zero code changes**: Just update config
✅ **Migration tool**: Automated data transfer
✅ **Production ready**: Qdrant for scale
✅ **Backward compatible**: FAISS still works

**Recommended setup:**
- **Development**: FAISS (simple, fast)
- **Production**: Qdrant (scalable, feature-rich)
