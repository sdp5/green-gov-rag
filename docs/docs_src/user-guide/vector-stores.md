# Vector Stores Guide

## Overview

GreenGovRAG supports multiple vector store backends through a factory pattern, allowing you to choose the best solution for your deployment:

- **FAISS** - Fast, in-memory vector search (ideal for development and small datasets)
- **Qdrant** - Production-grade, distributed vector database (recommended for production)
- **ChromaDB** - Coming soon

The factory pattern makes switching between backends as simple as updating a configuration value—no code changes required.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration](#configuration)
3. [Comparison: FAISS vs Qdrant](#comparison-faiss-vs-qdrant)
4. [Using the Factory](#using-the-factory)
5. [Migrating from FAISS to Qdrant](#migrating-from-faiss-to-qdrant)
6. [Common Operations](#common-operations)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)
9. [Performance Tips](#performance-tips)

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

# Use it
store.build_store(chunks)
results = store.similarity_search("emissions limits NSW", k=5)
```

### Configuration

Set in your `.env` file:

```bash
# Choose backend
VECTOR_STORE_TYPE=qdrant  # or 'faiss' or 'chromadb'

# FAISS settings (if using FAISS)
VECTOR_STORE_PATH=./data/vector_store

# Qdrant settings (if using Qdrant)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional for Qdrant Cloud
```

### Start Qdrant (if using Qdrant)

```bash
# Docker (recommended)
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant

# Verify it's running
curl http://localhost:6333/collections
```

## Configuration

### FAISS Setup

FAISS requires no server setup. Just specify the storage path:

```bash
# .env
VECTOR_STORE_TYPE=faiss
VECTOR_STORE_PATH=./data/vector_store
```

### Qdrant Setup

**Option A: Docker (Recommended)**
```bash
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
```

**Option B: Qdrant Cloud**
1. Sign up at https://qdrant.tech
2. Create a cluster
3. Get your API key and URL

**Option C: Docker Compose**
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

**Option D: Kubernetes (Helm)**
```bash
helm repo add qdrant https://qdrant.to/helm
helm install qdrant qdrant/qdrant
```

Then configure your application:

```bash
# .env
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional, only needed for Qdrant Cloud
```

### Installation

```bash
# Base installation (includes FAISS)
pip install -e .

# Add Qdrant support
pip install qdrant-client langchain-qdrant
```

## Comparison: FAISS vs Qdrant

| Feature | FAISS | Qdrant |
|---------|-------|--------|
| **Setup** | **Zero config | **Requires server |
| **Speed** | **Very fast (in-memory) | **Fast (network overhead) |
| **Scalability** | **Memory limited | **Millions of vectors |
| **Persistence** | **File-based | **Database-backed |
| **Metadata Filtering** | **Post-filtering (slow) | **Native filtering (fast) |
| **CRUD Operations** | **Add-only | **Full CRUD support |
| **Document Deletion** | **Not supported | **Supported |
| **List All Metadata** | **Not supported | **Supported |
| **Production Ready** | **Not recommended | **Production-grade |
| **High Availability** | **Single instance | **Clustering support |
| **Cost** | Free | Free (self-hosted) or Paid (cloud) |
| **Best For** | Development, demos | Production, large datasets |

### When to Use FAISS

- **Development and testing
- **Small datasets (<100K documents)
- **Single-server deployments
- **No need for deletion/updates
- **Simple setup required
- **Proof of concepts and demos

### When to Use Qdrant

- **Production deployments
- **Large datasets (>100K documents)
- **Need document deletion/updates
- **Complex metadata filtering
- **Multi-server/distributed setup
- **High availability required
- **Scalability is important

## Using the Factory

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
if not result['valid']:
    print(f"Issues: {result['issues']}")
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

## Migrating from FAISS to Qdrant

### Step 1: Install Dependencies

```bash
pip install qdrant-client langchain-qdrant
```

### Step 2: Start Qdrant Server

See [Configuration](#configuration) section above for setup options.

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
greengovrag-cli rag query "What are emissions limits in NSW?"
```

### Migration Troubleshooting

#### Issue: "FAISS doesn't support metadata listing"

**Problem**: FAISS can't list all documents, only search.

**Solution**: Migration script uses broad similarity searches to extract documents. This may not capture all documents in very large datasets.

**Better approach**: Re-embed from source documents
```bash
# Instead of migrating, rebuild from scratch
VECTOR_STORE_TYPE=qdrant python -m green_gov_rag.scripts.build_embeddings
```

#### Issue: "Qdrant connection failed"

**Problem**: Qdrant server not running.

**Solution**:
```bash
# Check if Qdrant is running
curl http://localhost:6333/collections

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Or check Qdrant Cloud URL/API key
```

#### Issue: "Migration is slow"

**Problem**: Large dataset taking too long.

**Solutions**:
1. Increase batch size: `--batch-size 5000`
2. Use direct database migration (Qdrant → Qdrant)
3. Re-embed in parallel using Airflow DAG

#### Issue: "Memory error during migration"

**Problem**: Too many documents loaded at once.

**Solution**: Reduce batch size
```bash
python -m green_gov_rag.scripts.migrate_vector_store \
    --batch-size 500  # Smaller batches
```

## Common Operations

### Building a Vector Store

```python
from green_gov_rag.rag.vector_store_factory import create_vector_store
from green_gov_rag.rag.embeddings import ChunkEmbedder

# Initialize
embeddings = ChunkEmbedder().embedder
store = create_vector_store(embeddings)

# Build from chunks
chunks = [
    {"content": "Climate policy document...", "metadata": {...}},
    {"content": "Emissions guidelines...", "metadata": {...}},
]
store.build_store(chunks)
```

### Similarity Search

```python
# Basic search
results = store.similarity_search("emissions limits NSW", k=5)

# With metadata filtering (Qdrant only)
results = store.similarity_search(
    "emissions limits NSW",
    k=5,
    filter={"jurisdiction": "NSW", "category": "environment"}
)

# Process results
for doc in results:
    print(f"Content: {doc.page_content}")
    print(f"Metadata: {doc.metadata}")
```

### Adding Documents

```python
# Add new documents
new_chunks = [
    {"content": "New regulation text...", "metadata": {...}},
]
store.add_chunks(new_chunks)
```

### Batch Operations

```python
# Add documents in batches for better performance
chunk_batches = [chunks[i:i+1000] for i in range(0, len(chunks), 1000)]
for batch in chunk_batches:
    store.add_chunks(batch)
```

## Production Deployment

### Qdrant Production Setup

**1. Deploy Qdrant**

See [Configuration](#configuration) section for deployment options:
- Docker Compose for single-server
- Kubernetes/Helm for multi-server
- Qdrant Cloud for managed service

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

**Custom Indexing:**
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

### Rollback Plan

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

## Troubleshooting

### Common Issues

#### Qdrant connection failed

```bash
# Check if Qdrant is running
curl http://localhost:6333/collections

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Check logs
docker logs <container_id>
```

#### Migration incomplete

```bash
# Use smaller batches
python -m green_gov_rag.scripts.migrate_vector_store \
  --batch-size 500  # Reduce from default 1000

# Or re-embed from scratch
VECTOR_STORE_TYPE=qdrant python -m green_gov_rag.scripts.build_embeddings
```

#### FAISS can't list all documents

FAISS limitation - use re-embedding instead:
```bash
# Re-embed directly to Qdrant
VECTOR_STORE_TYPE=qdrant python -m green_gov_rag.scripts.build_embeddings
```

#### Backend not available

```python
# Check available backends
from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

available = VectorStoreFactory.get_available_stores()
print(f"Available: {available}")

# Validate configuration
result = VectorStoreFactory.validate_config()
if not result['valid']:
    print(f"Issues: {result['issues']}")
```

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run operations with debug output
store = create_vector_store(embeddings)
results = store.similarity_search("test query", k=5)
```

## Performance Tips

### Qdrant Optimization

**Use GRPC for better performance:**
```python
store = create_vector_store(
    embeddings,
    store_type='qdrant',
    prefer_grpc=True  # Faster than HTTP
)
```

**Batch operations:**
```python
# Add documents in batches
chunks_batches = [chunks[i:i+1000] for i in range(0, len(chunks), 1000)]
for batch in chunks_batches:
    store.add_chunks(batch)
```

**Optimize HNSW index:**
```python
# Higher M = better recall, more memory
# Higher ef_construct = better indexing quality, slower
hnsw_config = models.HnswConfigDiff(
    m=16,           # Default: 16, range: 4-64
    ef_construct=100  # Default: 100, range: 4-512
)
```

### FAISS Optimization

**Use appropriate index type:**
```python
# For small datasets (<10K): Flat index (exact search)
# For medium datasets (10K-1M): IVF index
# For large datasets (>1M): HNSW or IVF+PQ
```

**Memory management:**
```python
# Keep index in memory for fast access
# Periodically save to disk
store.save("./data/vector_store")
```

## Backward Compatibility

### Old Code (Still Works)

```python
from green_gov_rag.rag.vector_store import VectorStore

# This still works, but shows deprecation warning
store = VectorStore(embeddings, index_path="./data/vector_store")
```

**Deprecation warning shown:**
```
VectorStore is deprecated. Use VectorStoreFactory.create_vector_store() instead.
See docs/user-guide/vector-stores.md for details.
```

### Recommended Update

```python
from green_gov_rag.rag.vector_store_factory import create_vector_store

# Modern approach
store = create_vector_store(embeddings)
```

## Future: ChromaDB Support

ChromaDB support is planned. To add it:

1. Implement `ChromaVectorStore` class
2. Add to factory in `vector_store_factory.py`
3. Similar interface to Qdrant

Stay tuned for updates!

## Summary

****Factory pattern** - Easy switching between backends
****Zero code changes** - Just update config
****Migration tool** - Automated data transfer
****Production ready** - Qdrant for scale
****Backward compatible** - FAISS still works

**Recommended setup:**
- **Development**: FAISS (simple, fast)
- **Production**: Qdrant (scalable, feature-rich)

## See Also

- [RAG Query Guide](./querying.md) - How to query the system
- [Caching Guide](./caching.md) - LLM response caching
- [Configuration Reference](../reference/config-reference.md) - All configuration options
- [API Reference](../api-reference/python/rag.md) - Python API documentation
