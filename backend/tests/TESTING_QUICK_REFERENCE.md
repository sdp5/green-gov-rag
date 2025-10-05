# Testing Quick Reference

**All external services auto-mocked. Just run `pytest`!**

## Quick Commands

```bash
# Run all tests
pytest tests/

# With coverage
pytest --cov=green_gov_rag tests/

# Specific file
pytest tests/test_rag.py -v

# Skip slow
pytest -m "not slow"

# Integration (requires Docker)
cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..
pytest -m integration
```

## Common Fixtures

```python
# Vector store
def test_search(in_memory_faiss):
    results = in_memory_faiss.similarity_search("query", k=3)

# Embeddings (mocked)
def test_embed(mock_embedder, sample_chunks):
    embedded = mock_embedder.embed_chunks(sample_chunks)

# Test data
def test_process(sample_chunks):  # 3 chunks pre-loaded
    pass
```

## Test Template

```python
def test_my_feature(in_memory_faiss, mock_embedder, sample_chunks):
    """Test description."""
    results = in_memory_faiss.similarity_search("test", k=2)
    assert len(results) <= 2
```

## Test Markers

```python
@pytest.mark.unit          # Default
@pytest.mark.integration   # Needs real services
@pytest.mark.slow          # >5 seconds
@pytest.mark.e2e          # End-to-end
```

## Debugging

```bash
# Verbose output
pytest tests/ -vv --showlocals

# Stop on first failure
pytest tests/ -x

# Drop into debugger
pytest tests/ --pdb

# Show print statements
pytest tests/ -s

# Profile slow tests
pytest tests/ --durations=10
```

## Coverage

```bash
# Generate HTML report
pytest --cov=green_gov_rag --cov-report=html tests/

# Open report
open htmlcov/index.html
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Real API calls | Check `tests/conftest.py` exists |
| Import errors | Run `pip install -e .[dev]` |
| Slow tests | Use `-m "not slow"` |
| Docker issues | Check `docker-compose ps` |

## Auto-Mocked

✅ OpenAI (embeddings + chat)
✅ AWS Bedrock
✅ HuggingFace
✅ AWS S3
✅ Azure Blob
✅ HTTP requests
✅ PostgreSQL

**No setup needed. Just test!**
