# Testing Quick Reference

## 🎯 TL;DR

**All external services are mocked automatically. Just write tests and run `pytest`!**

## 🚀 Quick Commands

```bash
# Run all tests (fast, mocked)
pytest tests/

# Run with coverage
pytest --cov=green_gov_rag tests/

# Run specific test file
pytest tests/test_rag.py -v

# Skip slow tests
pytest tests/ -m "not slow"

# Run only unit tests
pytest tests/ -m unit
```

## 📦 Key Fixtures (Auto-Mocked)

### Use These in Your Tests

```python
# Vector Store - Ready to use!
def test_search(in_memory_faiss):
    results = in_memory_faiss.similarity_search("query", k=3)

# Mock Embeddings - No API calls!
def test_embed(mock_embedder, sample_chunks):
    embedded = mock_embedder.embed_chunks(sample_chunks)

# Test Data - Pre-made samples
def test_process(sample_chunks, sample_documents):
    # sample_chunks has 3 chunks
    # sample_documents has 2 docs
    pass

# Temp Storage - Auto-cleanup
def test_storage(temp_data_dir):
    # temp_data_dir has raw/, processed/, chunks/
    pass
```

## 🐳 Integration Tests (Optional)

```bash
# Start test databases (from project root)
cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..

# Run integration tests
pytest tests/ -m integration

# Stop databases
cd tests && docker-compose -f docker-compose.test.yml down && cd ..
```

### Available Test Services
- PostgreSQL: `localhost:5433`
- Qdrant: `localhost:6334`
- LocalStack (AWS): `localhost:4566`
- Redis: `localhost:6380`

## ✅ What's Mocked Automatically

✅ OpenAI API (embeddings + chat)
✅ AWS Bedrock
✅ HuggingFace embeddings
✅ AWS S3 (boto3)
✅ Azure Blob Storage
✅ HTTP requests
✅ PostgreSQL connections
✅ Environment variables

**You don't need to mock anything yourself!**

## 📝 Test Template

```python
import pytest

def test_my_feature(
    in_memory_faiss,      # Vector store
    mock_embedder,        # Embeddings
    sample_chunks,        # Test data
    temp_data_dir         # Temp directory
):
    """Test description."""
    # Your test code here
    results = in_memory_faiss.similarity_search("test", k=2)
    assert len(results) <= 2
```

## 🏷️ Test Markers

```python
@pytest.mark.unit          # Unit test (default)
@pytest.mark.integration   # Needs real services
@pytest.mark.slow          # Takes >5 seconds
@pytest.mark.e2e          # End-to-end test
```

## 🔍 Common Test Patterns

### Test Vector Search
```python
def test_search(in_memory_faiss):
    results = in_memory_faiss.similarity_search("query", k=3)
    assert len(results) <= 3
```

### Test Embeddings
```python
def test_embeddings(mock_embedder, sample_chunks):
    embedded = mock_embedder.embed_chunks(sample_chunks)
    assert all("embedding" in e for e in embedded)
```

### Test Cloud Storage (Mocked)
```python
def test_upload(mock_s3_client, tmp_path):
    from green_gov_rag.cloud.storage import StorageClient

    client = StorageClient(provider="aws")
    file = tmp_path / "test.txt"
    file.write_text("test")

    client.upload_file(file, "bucket", "key")
    # Fully mocked, no real S3 calls!
```

### Test Database (SQLite)
```python
def test_db(test_db_path):
    import sqlite3
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    # Use like a real database
    cursor.execute("CREATE TABLE test (id INTEGER)")
    conn.commit()
```

## 🚨 Debugging Tests

### Verbose output
```bash
pytest tests/test_rag.py -vv --showlocals
```

### Stop on first failure
```bash
pytest tests/ -x
```

### Drop into debugger on failure
```bash
pytest tests/ --pdb
```

### Show print statements
```bash
pytest tests/ -s
```

### Profile slow tests
```bash
pytest tests/ --durations=10
```

## 📊 Coverage

```bash
# Generate coverage report
pytest --cov=green_gov_rag --cov-report=html tests/

# Open in browser
open htmlcov/index.html
```

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Tests calling real APIs | Ensure `tests/conftest.py` exists |
| Import errors | Run `pip install -e .[dev]` |
| Slow tests | Use `-m "not slow"` to skip |
| Docker not working | Check `docker-compose ps` |

## 📚 Full Documentation

- `tests/README.md` - Detailed test docs
- `tests/TEST_INFRASTRUCTURE.md` - Infrastructure overview
- `tests/conftest.py` - All fixtures

## 🎉 That's It!

**Just write your test and run `pytest`. Everything else is handled automatically!**

```python
def test_my_new_feature(in_memory_faiss, sample_chunks):
    # Test your code here
    pass
```

```bash
pytest tests/test_my_module.py -v
```

**No setup required. No external services needed. Just test!** ✨
