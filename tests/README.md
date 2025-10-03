# Test Infrastructure

## Overview

This test suite uses comprehensive mocking to avoid external service dependencies and provides options for test databases.

## Mocked External Services

### ✅ **Automatically Mocked (via conftest.py)**

All tests automatically mock the following external services:

1. **LLM/Embedding APIs**
   - OpenAI API (embeddings & chat completions)
   - AWS Bedrock (embeddings & LLM)
   - HuggingFace embeddings

2. **Cloud Storage**
   - AWS S3 (boto3 client)
   - Azure Blob Storage
   - Local storage (no mocking needed)

3. **HTTP Requests**
   - All `requests.get()` and `requests.post()` calls are mocked

4. **Environment Variables**
   - Test environment variables set automatically

## Test Database Options

### **Option 1: In-Memory Databases** ⭐ (Default)

**Fastest and requires no external dependencies**

#### Vector Database (FAISS)
```python
def test_my_feature(in_memory_faiss):
    # in_memory_faiss is a ready-to-use FAISS index
    results = in_memory_faiss.similarity_search("query", k=3)
    assert len(results) <= 3
```

#### Relational Database (SQLite)
```python
def test_db_operations(test_db_path):
    # test_db_path provides a temporary SQLite database
    import sqlite3
    conn = sqlite3.connect(test_db_path)
    # ... run tests
```

### **Option 2: Mocked PostgreSQL**

```python
def test_postgres_operations(mock_postgres_connection):
    # mock_postgres_connection provides a mocked psycopg2 connection
    cursor = mock_postgres_connection.cursor()
    cursor.execute("SELECT * FROM documents")
    results = cursor.fetchall()
```

### **Option 3: Docker-based Test Databases** (Not yet implemented)

For integration tests that need real database behavior:

```yaml
# docker-compose.test.yml
services:
  test-postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: greengovrag_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"

  test-qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6334:6333"
```

To use:
```bash
# Start test databases
cd tests && docker-compose -f docker-compose.test.yml up -d

# Run integration tests (from project root)
pytest tests/ --integration

# Stop test databases
cd tests && docker-compose -f docker-compose.test.yml down
```

## Available Fixtures

### Mock Service Fixtures

| Fixture | Description | Usage |
|---------|-------------|-------|
| `mock_openai_embeddings` | Mock OpenAI embeddings API | Returns 384-dim vectors |
| `mock_huggingface_embeddings` | Mock HuggingFace embeddings | Returns 384-dim vectors |
| `mock_bedrock_embeddings` | Mock AWS Bedrock embeddings | Returns mock embeddings |
| `mock_openai_chat` | Mock OpenAI chat completions | Returns test responses |
| `mock_s3_client` | Mock AWS S3 client | All S3 operations mocked |
| `mock_azure_blob` | Mock Azure Blob Storage | All blob operations mocked |
| `mock_embedder` | Mock chunk embedder | No external API calls |

### Database Fixtures

| Fixture | Description | Usage |
|---------|-------------|-------|
| `in_memory_faiss` | In-memory FAISS vector store | Pre-populated with sample data |
| `temp_vector_store` | Temporary FAISS index path | For persistence tests |
| `test_db_path` | Temporary SQLite database | For SQL tests |
| `mock_postgres_connection` | Mocked PostgreSQL connection | For unit tests |

### Data Fixtures

| Fixture | Description |
|---------|-------------|
| `sample_chunks` | Sample document chunks with metadata |
| `sample_documents` | Sample document metadata |
| `temp_data_dir` | Temporary directory with data structure |

### Auto-use Fixtures

These fixtures are applied to ALL tests automatically:

- `mock_env_vars` - Sets test environment variables
- `disable_external_requests` - Prevents accidental HTTP calls
- `clean_import_cache` - Ensures test isolation

## Running Tests

### Run all tests (with mocks)
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_rag.py -v
```

### Run with coverage
```bash
pytest --cov=green_gov_rag tests/
```

### Run integration tests (requires real services)
```bash
# Set environment variables for real services
export RUN_CLOUD_INTEGRATION_TESTS=true
export TEST_AWS=true
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

pytest tests/ -m integration
```

### Skip slow tests
```bash
pytest tests/ -m "not slow"
```

## Test Categories

### Unit Tests
- Mock all external dependencies
- Fast execution
- No network calls
- Default for all tests

### Integration Tests
- Use real services (opt-in)
- Require credentials
- Slower execution
- Mark with `@pytest.mark.integration`

### End-to-End Tests
- Full pipeline tests
- Can use test databases
- Mark with `@pytest.mark.e2e`

## Writing New Tests

### Example: Test with Mocked Embeddings

```python
def test_embedding_generation(mock_embedder, sample_chunks):
    """Test embedding generation without external API calls."""
    embedded = mock_embedder.embed_chunks(sample_chunks)

    assert len(embedded) == len(sample_chunks)
    for chunk in embedded:
        assert "embedding" in chunk
        assert len(chunk["embedding"]) == 384
```

### Example: Test with In-Memory FAISS

```python
def test_vector_search(in_memory_faiss):
    """Test vector similarity search."""
    results = in_memory_faiss.similarity_search(
        "carbon emissions",
        k=2,
        filter={"region": "NSW"}
    )

    assert len(results) <= 2
    for doc in results:
        assert doc.metadata["region"] == "NSW"
```

### Example: Test with Temporary Database

```python
def test_data_persistence(test_db_path):
    """Test data persistence with SQLite."""
    import sqlite3

    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT
        )
    """)

    cursor.execute(
        "INSERT INTO documents (title, content) VALUES (?, ?)",
        ("Test Doc", "Test content")
    )
    conn.commit()

    cursor.execute("SELECT * FROM documents")
    results = cursor.fetchall()

    assert len(results) == 1
    assert results[0][1] == "Test Doc"

    conn.close()
```

### Example: Integration Test (Opt-in)

```python
import pytest
import os

@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("TEST_AWS") != "true",
    reason="AWS integration tests not enabled"
)
def test_real_s3_upload():
    """Test actual S3 upload (requires real credentials)."""
    from green_gov_rag.cloud.storage import StorageClient

    client = StorageClient(provider="aws")
    # ... test with real S3
```

## Test Database Recommendations

### When to Use Each Option

| Use Case | Recommendation |
|----------|---------------|
| Unit tests for business logic | In-memory FAISS + Mocked DB |
| Testing FAISS operations | `in_memory_faiss` fixture |
| Testing SQL queries | `test_db_path` (SQLite) |
| Testing PostgreSQL-specific features | `mock_postgres_connection` |
| Integration tests | Docker databases |
| CI/CD pipeline | In-memory databases |
| Local development | Docker databases (optional) |

### Performance Comparison

| Database Type | Speed | Setup | Isolation |
|--------------|-------|-------|-----------|
| In-memory FAISS | ⚡⚡⚡ | None | ✅ Perfect |
| SQLite | ⚡⚡⚡ | None | ✅ Perfect |
| Mocked Postgres | ⚡⚡⚡ | None | ✅ Perfect |
| Docker Postgres | ⚡ | Docker | ✅ Good |
| Real Services | ⚡ | Complex | ⚠️ Shared |

## Continuous Integration

The test suite is designed to run in CI/CD without any external dependencies:

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -e .[dev]
      - run: pytest tests/ --cov=green_gov_rag
      # No external services needed! All mocked automatically
```

## Troubleshooting

### Tests are making real API calls
- Check that `conftest.py` is in the `tests/` directory
- Ensure fixtures are imported correctly
- Use `pytest -v` to see which fixtures are active

### FAISS import errors
```bash
pip install faiss-cpu
# or for GPU support:
pip install faiss-gpu
```

### Database connection errors
- For unit tests: Use mocks (no real connection needed)
- For integration tests: Check Docker is running
- Verify environment variables are set

### Slow tests
```bash
# Profile test execution
pytest tests/ --durations=10

# Run only fast tests
pytest tests/ -m "not slow"
```

## Future Enhancements

- [ ] Add pytest-docker for automated Docker test databases
- [ ] Add Qdrant test instance support
- [ ] Add test data factories (using factory_boy)
- [ ] Add property-based testing (using hypothesis)
- [ ] Add async test support for async operations
