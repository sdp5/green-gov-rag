# Test Infrastructure

## Overview

Comprehensive mocking of external services with flexible database options.

## Auto-Mocked Services

✅ **LLM/Embedding APIs** - OpenAI, AWS Bedrock, HuggingFace
✅ **Cloud Storage** - AWS S3, Azure Blob
✅ **HTTP Requests** - All `requests` calls
✅ **Environment Variables** - Test-specific values

## Database Options

### 1. In-Memory (Default) ⭐

**Fastest, no setup**

```python
def test_with_faiss(in_memory_faiss):
    results = in_memory_faiss.similarity_search("query", k=3)

def test_with_sqlite(test_db_path):
    conn = sqlite3.connect(test_db_path)
```

### 2. Docker Test Databases

```bash
# Start
cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..

# Run tests
pytest -m integration

# Stop
cd tests && docker-compose -f docker-compose.test.yml down && cd ..
```

**Services:**
- PostgreSQL: `localhost:5433`
- Qdrant: `localhost:6334`
- LocalStack (AWS): `localhost:4566`
- Redis: `localhost:6380`

### 3. Mocked Postgres

```python
def test_postgres(mock_postgres_connection):
    cursor = mock_postgres_connection.cursor()
```

## Key Fixtures

| Fixture | Purpose |
|---------|---------|
| `in_memory_faiss` | Vector store with sample data |
| `mock_embedder` | No API calls |
| `mock_openai_chat` | Mock chat completions |
| `mock_s3_client` | Mock S3 operations |
| `sample_chunks` | 3 test chunks |
| `temp_data_dir` | Temporary directory |

## Running Tests

```bash
# All tests (mocked)
pytest tests/

# With coverage
pytest --cov=green_gov_rag tests/

# Integration tests
pytest -m integration

# Skip slow
pytest -m "not slow"

# Specific file
pytest tests/test_rag.py -v
```

## Writing Tests

### Basic Pattern

```python
def test_my_feature(in_memory_faiss, mock_embedder, sample_chunks):
    """Test description."""
    results = in_memory_faiss.similarity_search("test", k=2)
    assert len(results) <= 2
```

### Integration Test

```python
@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("TEST_AWS") != "true",
    reason="AWS tests not enabled"
)
def test_real_s3():
    # Test with real AWS
    pass
```

## Database Comparison

| Type | Speed | Setup | Best For |
|------|-------|-------|----------|
| In-memory | ⚡⚡⚡ | None | Unit tests |
| Docker | ⚡⚡ | Docker | Integration |
| Real | ⚡ | Complex | E2E |

## CI/CD

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -e .[dev]
      - run: pytest tests/ --cov=green_gov_rag
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Real API calls | Check `conftest.py` exists |
| FAISS errors | `pip install faiss-cpu` |
| Docker issues | `docker-compose ps` |
| Slow tests | Use `-m "not slow"` |

## Configuration

**pytest.ini** (in `pyproject.toml`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: unit tests",
    "integration: requires real services",
    "slow: slow tests",
    "e2e: end-to-end tests",
]
```

**Coverage** (in `pyproject.toml`):
```toml
[tool.coverage.run]
source = ["green_gov_rag"]
omit = ["*/tests/*"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]
```
