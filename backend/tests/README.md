# Test Suite

## Quick Start

```bash
# Install dependencies
pip install -e .[dev]

# Run all tests
pytest tests/

# Run with coverage
pytest --cov=green_gov_rag tests/
```

## Key Features

✅ **Auto-mocked** - All external services mocked automatically (OpenAI, AWS, Azure, HTTP)
✅ **Fast** - In-memory databases (FAISS, SQLite)
✅ **Isolated** - No external dependencies required

## Common Fixtures

```python
# Vector store
def test_search(in_memory_faiss):
    results = in_memory_faiss.similarity_search("query", k=3)

# Mock embeddings
def test_embed(mock_embedder, sample_chunks):
    embedded = mock_embedder.embed_chunks(sample_chunks)

# Test data
def test_process(sample_chunks, sample_documents):
    # 3 chunks, 2 documents pre-loaded
    pass
```

## Test Commands

```bash
# Specific test file
pytest tests/test_rag.py -v

# Skip slow tests
pytest -m "not slow"

# Integration tests (requires Docker)
cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..
pytest -m integration
```

## Test Markers

- `@pytest.mark.unit` - Unit test (default)
- `@pytest.mark.integration` - Requires real services
- `@pytest.mark.slow` - Takes >5 seconds
- `@pytest.mark.e2e` - End-to-end test

## Documentation

- `TEST_INFRASTRUCTURE.md` - Infrastructure details
- `TESTING_QUICK_REFERENCE.md` - Quick reference
- `conftest.py` - All fixtures
