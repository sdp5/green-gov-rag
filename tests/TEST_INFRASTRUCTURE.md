# Test Infrastructure Summary

## 🎯 Overview

The GreenGovRAG test infrastructure provides comprehensive mocking of external services and flexible database options for testing.

## ✅ What's Been Implemented

### 1. **Comprehensive Test Mocking** (`tests/conftest.py`)

All external services are automatically mocked to enable fast, isolated unit tests:

#### **LLM & Embedding Services**
- ✅ OpenAI API (embeddings + chat)
- ✅ AWS Bedrock (embeddings + LLM)
- ✅ HuggingFace embeddings
- ✅ Mock embedder for testing without APIs

#### **Cloud Storage Services**
- ✅ AWS S3 (boto3)
- ✅ Azure Blob Storage
- ✅ HTTP requests (requests library)

#### **Database Services**
- ✅ PostgreSQL (psycopg2) - mocked
- ✅ FAISS vector store - in-memory
- ✅ SQLite - temporary files

### 2. **Test Database Options**

#### **Option 1: In-Memory (Default)** ⭐
```python
# Fast, no external dependencies
def test_with_faiss(in_memory_faiss):
    results = in_memory_faiss.similarity_search("query", k=3)

def test_with_sqlite(test_db_path):
    conn = sqlite3.connect(test_db_path)
```

#### **Option 2: Docker Test Databases**
```bash
# Start test databases
cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..

# Run integration tests
pytest tests/ --integration

# Stop databases
cd tests && docker-compose -f docker-compose.test.yml down && cd ..
```

**Available test services:**
- PostgreSQL (port 5433)
- Qdrant vector DB (port 6334)
- LocalStack (AWS mocking, port 4566)
- Redis (port 6380)

#### **Option 3: Mocked Databases**
```python
# For unit tests only
def test_postgres(mock_postgres_connection):
    cursor = mock_postgres_connection.cursor()
    cursor.execute("SELECT * FROM docs")
```

## 📦 Test Fixtures Available

### Mock Service Fixtures

| Fixture | Purpose | Returns |
|---------|---------|---------|
| `mock_openai_embeddings` | Mock OpenAI API | 384-dim vectors |
| `mock_huggingface_embeddings` | Mock HuggingFace | 384-dim vectors |
| `mock_bedrock_embeddings` | Mock AWS Bedrock | Mock embeddings |
| `mock_openai_chat` | Mock chat completions | Test responses |
| `mock_s3_client` | Mock S3 operations | Mocked boto3 client |
| `mock_azure_blob` | Mock Azure storage | Mocked blob client |
| `mock_embedder` | Mock chunk embedder | No API calls |

### Database Fixtures

| Fixture | Purpose | Usage |
|---------|---------|-------|
| `in_memory_faiss` | FAISS vector store | Pre-populated, ready to query |
| `temp_vector_store` | Temp FAISS path | For persistence tests |
| `test_db_path` | SQLite database | Temporary file path |
| `mock_postgres_connection` | Mocked Postgres | For unit tests |

### Data Fixtures

| Fixture | Content |
|---------|---------|
| `sample_chunks` | 3 document chunks with metadata |
| `sample_documents` | 2 document configs |
| `temp_data_dir` | Temporary data directory structure |

### Auto-Applied Fixtures

These run automatically for ALL tests:
- `mock_env_vars` - Test environment variables
- `disable_external_requests` - Prevents HTTP calls
- `clean_import_cache` - Test isolation

## 🚀 Running Tests

### Quick Start
```bash
# Install dependencies
pip install -e .[dev]

# Run all tests (mocked, fast)
pytest tests/

# Run with coverage
pytest --cov=green_gov_rag tests/

# Run specific test
pytest tests/test_cloud_storage.py -v
```

### Advanced Usage
```bash
# Run only unit tests (default)
pytest tests/ -m unit

# Run integration tests (requires Docker)
cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..
pytest tests/ -m integration
cd tests && docker-compose -f docker-compose.test.yml down && cd ..

# Skip slow tests
pytest tests/ -m "not slow"

# Run with detailed output
pytest tests/ -vv --showlocals

# Profile slow tests
pytest tests/ --durations=10
```

## 📝 Writing New Tests

### Example 1: Unit Test with Mocks

```python
def test_embeddings(mock_embedder, sample_chunks):
    """Test without external API calls."""
    embedded = mock_embedder.embed_chunks(sample_chunks)

    assert len(embedded) == len(sample_chunks)
    for chunk in embedded:
        assert "embedding" in chunk
        assert len(chunk["embedding"]) == 384
```

### Example 2: Test with In-Memory FAISS

```python
def test_vector_search(in_memory_faiss):
    """Test similarity search."""
    results = in_memory_faiss.similarity_search(
        "carbon emissions",
        k=2,
        filter={"region": "NSW"}
    )

    assert len(results) <= 2
    assert all(d.metadata["region"] == "NSW" for d in results)
```

### Example 3: Integration Test (Opt-in)

```python
import pytest
import os

@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("TEST_AWS") != "true",
    reason="AWS tests not enabled"
)
def test_real_s3():
    """Test with real S3 (requires credentials)."""
    from green_gov_rag.cloud.storage import StorageClient

    client = StorageClient(provider="aws")
    # Test with real AWS S3
```

## 🔧 Configuration

### pytest.ini (in pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: slow tests",
    "integration: requires real services",
    "e2e: end-to-end tests",
    "unit: unit tests (default)",
]
```

### Coverage Settings

```toml
[tool.coverage.run]
source = ["green_gov_rag"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## 🐳 Docker Test Databases

### Services Provided

1. **PostgreSQL** (port 5433)
   - Database: `greengovrag_test`
   - User: `test_user`
   - Password: `test_password`

2. **Qdrant Vector DB** (port 6334)
   - Alternative to FAISS
   - Persistent storage

3. **LocalStack** (port 4566)
   - Mock AWS services (S3, Bedrock)
   - No AWS credentials needed

4. **Redis** (port 6380)
   - Caching test data

### Usage

```bash
# Start all test services (from project root)
cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..

# Check service health
cd tests && docker-compose -f docker-compose.test.yml ps && cd ..

# View logs
cd tests && docker-compose -f docker-compose.test.yml logs -f && cd ..

# Stop and remove
cd tests && docker-compose -f docker-compose.test.yml down -v && cd ..
```

### Connect to Test Databases

```python
# PostgreSQL
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="greengovrag_test",
    user="test_user",
    password="test_password"
)

# Qdrant
from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6334)

# LocalStack S3
import boto3
s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test"
)
```

## 📊 Test Database Comparison

| Database Type | Speed | Setup | Isolation | Best For |
|--------------|-------|-------|-----------|----------|
| In-memory FAISS | ⚡⚡⚡ | None | ✅ Perfect | Unit tests |
| SQLite | ⚡⚡⚡ | None | ✅ Perfect | Unit tests |
| Mocked Postgres | ⚡⚡⚡ | None | ✅ Perfect | Unit tests |
| Docker Postgres | ⚡⚡ | Docker | ✅ Good | Integration |
| Docker Qdrant | ⚡⚡ | Docker | ✅ Good | Integration |
| Real Services | ⚡ | Complex | ⚠️ Shared | E2E tests |

## 🎯 Recommendations

### For Different Test Types

| Test Type | Use |
|-----------|-----|
| **Unit Tests** | In-memory FAISS + Mocks |
| **Integration Tests** | Docker databases |
| **CI/CD Pipeline** | In-memory only (fastest) |
| **Local Development** | Docker (optional) |
| **E2E Tests** | Real services (staging) |

### Performance Tips

1. **Default to mocks** - Fastest, no setup
2. **Use in-memory FAISS** - No persistence needed for most tests
3. **Docker for integration** - When you need real DB behavior
4. **Mark slow tests** - Skip during development
5. **Isolate tests** - Use fixtures for cleanup

## 🚨 Troubleshooting

### Tests making real API calls
✅ **Solution**: Ensure `conftest.py` is present in `tests/`

### FAISS import errors
```bash
pip install faiss-cpu
```

### Docker connection issues
```bash
# Check services are running
cd tests && docker-compose -f docker-compose.test.yml ps && cd ..

# Restart services
cd tests && docker-compose -f docker-compose.test.yml restart && cd ..
```

### Slow test execution
```bash
# Profile tests
pytest tests/ --durations=10

# Run only fast tests
pytest tests/ -m "not slow"
```

## 📈 CI/CD Integration

### GitHub Actions (Example)

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
      # No external services needed!
```

### With Docker (Optional)

```yaml
jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: cd tests && docker-compose -f docker-compose.test.yml up -d
      - run: pip install -e .[dev]
      - run: pytest tests/ -m integration
      - run: cd tests && docker-compose -f docker-compose.test.yml down
```

## 📚 Files Created

1. ✅ `tests/conftest.py` - Main fixture configuration
2. ✅ `tests/README.md` - Detailed test documentation
3. ✅ `tests/docker-compose.test.yml` - Test database services
4. ✅ `tests/TEST_INFRASTRUCTURE.md` - This infrastructure overview
5. ✅ `tests/TESTING_QUICK_REFERENCE.md` - Quick reference guide
6. ✅ `pyproject.toml` - Updated with pytest config

## 🔄 Next Steps

To use the test infrastructure:

1. **Install dependencies**
   ```bash
   pip install -e .[dev]
   ```

2. **Run tests**
   ```bash
   pytest tests/
   ```

3. **(Optional) Start Docker databases**
   ```bash
   cd tests && docker-compose -f docker-compose.test.yml up -d && cd ..
   ```

4. **Write new tests** using fixtures from `conftest.py`

## ✨ Key Benefits

✅ **No external dependencies** for unit tests
✅ **Fast execution** with in-memory databases
✅ **Perfect isolation** between tests
✅ **Easy CI/CD integration**
✅ **Optional Docker** for integration testing
✅ **Comprehensive mocking** of all external services
✅ **Flexible database options** for different needs

---

**All external services are mocked by default. Your tests will run fast and reliably without any external dependencies!** 🚀
