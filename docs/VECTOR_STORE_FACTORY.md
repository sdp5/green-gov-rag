# Vector Store Factory - Quick Reference

## ✅ What's Been Implemented

### 1. **Factory Pattern**
- `VectorStoreFactory` - Central factory for creating vector stores
- `VectorStoreInterface` - Common interface for all backends
- `FAISSVectorStore` - FAISS implementation
- `QdrantVectorStore` - Qdrant implementation (production-ready)
- ChromaDB - Coming soon

### 2. **Migration Tool**
- `migrate_vector_store.py` - Automated migration between backends
- Batch processing for large datasets
- Dry-run mode for testing
- Progress tracking and error handling

### 3. **Configuration**
- Qdrant dependencies added to `pyproject.toml`
- Configuration already in place (`.env`)
- Backward compatibility maintained

## 🚀 Quick Start

### Using the Factory (New Code)

```python
from green_gov_rag.rag.vector_store_factory import create_vector_store
from green_gov_rag.rag.embeddings import ChunkEmbedder

# Initialize
embeddings = ChunkEmbedder().embedder

# Use configured backend (from .env)
store = create_vector_store(embeddings)

# Or explicitly choose
store = create_vector_store(embeddings, store_type='qdrant')

# Use it
store.build_store(chunks)
results = store.similarity_search("emissions limits NSW", k=5)
```

### Configuration (`.env`)

```bash
# Choose your backend
VECTOR_STORE_TYPE=qdrant  # or 'faiss'

# FAISS config (if using FAISS)
VECTOR_STORE_PATH=./data/vector_store

# Qdrant config (if using Qdrant)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional
```

### Start Qdrant

```bash
# Docker (easiest)
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant

# Verify
curl http://localhost:6333/collections
```

## 📦 Migration from FAISS to Qdrant

### One-Line Migration

```bash
python -m green_gov_rag.scripts.migrate_vector_store \
  --source faiss --target qdrant
```

### With Options

```bash
python -m green_gov_rag.scripts.migrate_vector_store \
  --source faiss \
  --target qdrant \
  --source-path ./data/vector_store \
  --batch-size 1000 \
  --dry-run  # Remove for actual migration
```

### Update Config

```bash
# .env
VECTOR_STORE_TYPE=qdrant
```

Done! Your app now uses Qdrant.

## 🔍 Feature Comparison

| Feature | FAISS | Qdrant |
|---------|-------|--------|
| **Setup** | ✅ Zero config | ⚠️ Requires server |
| **Speed** | ✅ Very fast | ✅ Fast |
| **Scalability** | ❌ Memory limited | ✅ Millions of vectors |
| **Metadata Filter** | ⚠️ Post-filter (slow) | ✅ Native (fast) |
| **Delete Docs** | ❌ Not supported | ✅ Supported |
| **List Metadata** | ❌ Not supported | ✅ Supported |
| **Production** | ❌ Not recommended | ✅ Production-ready |
| **Persistence** | ⚠️ File-based | ✅ Database-backed |
| **Best For** | Dev/Small datasets | Production/Scale |

## 📊 Use Cases

### When to Use FAISS
- ✅ Development and testing
- ✅ Small datasets (<100K documents)
- ✅ Single-server deployments
- ✅ No need for deletion/updates
- ✅ Simple setup required

### When to Use Qdrant
- ✅ Production deployments
- ✅ Large datasets (>100K documents)
- ✅ Need document deletion/updates
- ✅ Complex metadata filtering
- ✅ Multi-server/distributed setup
- ✅ High availability required

## 🛠️ API Examples

### Check Available Backends

```python
from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

# See what's available
backends = VectorStoreFactory.get_available_stores()
print(backends)  # ['faiss', 'qdrant']
```

### Validate Configuration

```python
# Validate current config
result = VectorStoreFactory.validate_config()
if not result['valid']:
    print(f"Issues: {result['issues']}")

# Validate specific backend
qdrant_check = VectorStoreFactory.validate_config('qdrant')
print(qdrant_check)
```

### Get Store Info

```python
store = create_vector_store(embeddings)
info = store.get_store_info()
print(f"Backend: {info['backend']}")
print(f"Documents: {info['document_count']}")
print(f"Can delete: {info['supports_deletion']}")
```

### Delete Documents (Qdrant Only)

```python
store = create_vector_store(embeddings, store_type='qdrant')
store.delete_by_id(['doc_123', 'doc_456'])
```

### List All Metadata (Qdrant Only)

```python
store = create_vector_store(embeddings, store_type='qdrant')
all_metadata = store.list_metadata()
print(f"Total documents: {len(all_metadata)}")
```

## 🔄 Backward Compatibility

### Old Code (Still Works)

```python
from green_gov_rag.rag.vector_store import VectorStore

# This still works, but shows deprecation warning
store = VectorStore(embeddings, index_path="./data/vector_store")
```

**Deprecation warning shown:**
```
VectorStore is deprecated. Use VectorStoreFactory.create_vector_store() instead.
See docs/VECTOR_STORE_MIGRATION.md for details.
```

### Recommended Update

```python
from green_gov_rag.rag.vector_store_factory import create_vector_store

# Modern approach
store = create_vector_store(embeddings)
```

## 🚨 Troubleshooting

### Issue: Qdrant connection failed
```bash
# Check if Qdrant is running
curl http://localhost:6333/collections

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant
```

### Issue: Migration incomplete
```bash
# Use smaller batches
python -m green_gov_rag.scripts.migrate_vector_store \
  --batch-size 500  # Reduce from default 1000
```

### Issue: FAISS can't list all documents
FAISS limitation - use re-embedding instead:
```bash
# Re-embed directly to Qdrant
VECTOR_STORE_TYPE=qdrant python -m green_gov_rag.scripts.build_embeddings
```

## 📈 Performance Tips

### Qdrant Optimization

```python
# Use GRPC for better performance (if supported)
store = create_vector_store(
    embeddings,
    store_type='qdrant',
    prefer_grpc=True
)
```

### Batch Operations

```python
# Add documents in batches for better performance
chunks_batches = [chunks[i:i+1000] for i in range(0, len(chunks), 1000)]
for batch in chunks_batches:
    store.add_chunks(batch)
```

## 📝 Summary

✅ **Factory pattern implemented** - Easy backend switching
✅ **FAISS + Qdrant supported** - ChromaDB coming soon
✅ **Migration tool ready** - Automated FAISS → Qdrant
✅ **Backward compatible** - Old code still works
✅ **Production ready** - Qdrant for scale
✅ **Well documented** - Complete guides available

**Next Steps:**
1. Try Qdrant locally: `docker run -p 6333:6333 qdrant/qdrant`
2. Run migration: `python -m green_gov_rag.scripts.migrate_vector_store --dry-run`
3. Update config: `VECTOR_STORE_TYPE=qdrant`
4. Enjoy production-grade vector search! 🚀

**Documentation:**
- Full migration guide: `docs/VECTOR_STORE_MIGRATION.md`
- Caching guide: `docs/CACHING.md`
- Main README: `README.md`
