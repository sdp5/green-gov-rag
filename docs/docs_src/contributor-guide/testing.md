# Testing Guide

> Comprehensive guide to testing in GreenGovRAG

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Unit Tests](#writing-unit-tests)
- [Writing Integration Tests](#writing-integration-tests)
- [Test Markers](#test-markers)
- [Mocking and Fixtures](#mocking-and-fixtures)
- [Code Coverage](#code-coverage)
- [Testing Best Practices](#testing-best-practices)
- [CI/CD Testing](#cicd-testing)
- [Debugging Tests](#debugging-tests)

## Overview

Testing is a critical part of GreenGovRAG's development process. We maintain high test coverage to ensure reliability, catch regressions early, and enable confident refactoring.

### Testing Philosophy

- **Write tests first** (Test-Driven Development encouraged)
- **Test behavior, not implementation** (focus on what, not how)
- **Keep tests simple and readable** (tests are documentation)
- **Isolate tests** (no dependencies between tests)
- **Fast feedback** (unit tests should run in milliseconds)
- **Comprehensive coverage** (aim for 70%+ overall, 90%+ for core logic)

### Test Types

1. **Unit Tests**: Test individual functions/classes in isolation
2. **Integration Tests**: Test interactions between components
3. **End-to-End Tests**: Test complete workflows (future enhancement)
4. **Performance Tests**: Benchmark critical paths (future enhancement)

### Testing Framework

We use **pytest** with these key plugins:
- `pytest-cov`: Code coverage reporting
- `pytest-mock`: Simplified mocking
- `pytest-asyncio`: Async test support

## Test Structure

### Directory Organization

```
backend/tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_api/                # API endpoint tests
│   ├── __init__.py
│   ├── test_query.py
│   ├── test_documents.py
│   └── test_admin.py
├── test_rag/                # RAG component tests
│   ├── __init__.py
│   ├── test_vector_store.py
│   ├── test_enhanced_response.py
│   ├── test_llm_factory.py
│   └── test_hybrid_search.py
├── test_etl/                # ETL pipeline tests
│   ├── __init__.py
│   ├── test_pipeline.py
│   ├── test_ingest.py
│   ├── test_chunker.py
│   └── test_sources/
│       ├── test_epbc_scraper.py
│       └── test_sa_legislation.py
├── test_models/             # Database model tests
│   ├── __init__.py
│   └── test_document.py
├── fixtures/                # Test data files
│   ├── sample_documents/
│   │   ├── test.pdf
│   │   └── test.html
│   └── mock_responses/
│       └── llm_responses.json
└── utils.py                 # Test utilities and helpers
```

### Test File Naming

```python
# Good: Follows pytest discovery pattern
test_vector_store.py
test_enhanced_response.py
test_query_endpoint.py

# Bad: Won't be discovered by pytest
vector_store_test.py
tests_for_rag.py
rag.py
```

### Test Function Naming

```python
# Good: Descriptive test names
def test_query_endpoint_returns_relevant_documents():
    """Test that query endpoint returns relevant documents."""
    pass

def test_vector_store_handles_empty_query():
    """Test vector store behavior with empty query."""
    pass

def test_metadata_tagger_extracts_jurisdiction():
    """Test metadata tagger extracts jurisdiction correctly."""
    pass

# Bad: Vague test names
def test_query():
    pass

def test_vector_store():
    pass

def test_1():
    pass
```

## Running Tests

### Basic Test Execution

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_rag/test_vector_store.py

# Run specific test function
pytest tests/test_rag/test_vector_store.py::test_faiss_similarity_search

# Run tests matching pattern
pytest -k "vector_store"
pytest -k "test_query or test_search"

# Verbose output
pytest -v

# Very verbose (show print statements)
pytest -vv

# Stop on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3

# Run last failed tests
pytest --lf

# Run failed tests first, then others
pytest --ff
```

### Running by Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run integration but not slow
pytest -m "integration and not slow"

# Run unit and integration
pytest -m "unit or integration"
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest -n auto

# Run tests on 4 cores
pytest -n 4
```

### Running with Coverage

```bash
# Run with coverage report
pytest --cov=green_gov_rag

# HTML coverage report
pytest --cov=green_gov_rag --cov-report=html

# XML coverage report (for CI)
pytest --cov=green_gov_rag --cov-report=xml

# Show missing lines
pytest --cov=green_gov_rag --cov-report=term-missing

# Coverage for specific module
pytest --cov=green_gov_rag.rag --cov-report=html
```

## Writing Unit Tests

Unit tests verify individual functions or classes in isolation.

### Basic Unit Test

```python
"""Tests for document chunking functionality."""

from green_gov_rag.etl.chunker import chunk_text


def test_chunk_text_splits_by_size():
    """Test that chunk_text splits text into correct sizes."""
    text = "a" * 2500
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100)

    assert len(chunks) == 3
    assert len(chunks[0]) == 1000
    assert len(chunks[1]) == 1000
    assert len(chunks[2]) == 500


def test_chunk_text_maintains_overlap():
    """Test that chunks maintain specified overlap."""
    text = "abcdefghij" * 200  # 2000 chars
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100)

    # Verify overlap between consecutive chunks
    overlap = chunks[0][-100:]
    start_of_next = chunks[1][:100]
    assert overlap == start_of_next


def test_chunk_text_handles_empty_input():
    """Test that chunk_text handles empty string."""
    chunks = chunk_text("", chunk_size=1000)

    assert chunks == []


def test_chunk_text_with_text_smaller_than_chunk_size():
    """Test chunking text smaller than chunk size."""
    text = "Short text"
    chunks = chunk_text(text, chunk_size=1000)

    assert len(chunks) == 1
    assert chunks[0] == text
```

### Testing Classes

```python
"""Tests for DocumentProcessor class."""

import pytest
from pathlib import Path

from green_gov_rag.etl.ingest import DocumentProcessor
from green_gov_rag.models.document import Document


class TestDocumentProcessor:
    """Test suite for DocumentProcessor."""

    def test_init_sets_default_values(self):
        """Test that initialization sets correct defaults."""
        processor = DocumentProcessor()

        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
        assert processor.enable_ocr is False

    def test_init_accepts_custom_values(self):
        """Test initialization with custom values."""
        processor = DocumentProcessor(
            chunk_size=500,
            chunk_overlap=50,
            enable_ocr=True,
        )

        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 50
        assert processor.enable_ocr is True

    def test_process_file_returns_chunks(self, tmp_path):
        """Test that process_file returns document chunks."""
        # Create temporary test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content " * 100)

        processor = DocumentProcessor(chunk_size=100)
        chunks = processor.process_file(test_file)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_process_file_raises_on_missing_file(self):
        """Test that process_file raises error for missing file."""
        processor = DocumentProcessor()

        with pytest.raises(FileNotFoundError):
            processor.process_file(Path("nonexistent.txt"))
```

### Testing with Parametrize

```python
"""Tests using parametrization."""

import pytest
from green_gov_rag.rag.location_ner import extract_location


@pytest.mark.parametrize(
    "query,expected_location",
    [
        ("What are the rules in Adelaide?", "Adelaide"),
        ("Can I build in Dubbo Regional?", "Dubbo Regional"),
        ("Regulations for Sydney City Council", "Sydney"),
        ("Rules in South Australia", "South Australia"),
    ],
)
def test_extract_location_finds_australian_locations(query, expected_location):
    """Test location extraction from various queries."""
    location = extract_location(query)

    assert expected_location.lower() in location.lower()


@pytest.mark.parametrize(
    "chunk_size,chunk_overlap",
    [
        (1000, 100),
        (500, 50),
        (2000, 200),
    ],
)
def test_chunker_with_various_sizes(chunk_size, chunk_overlap):
    """Test chunking with different size parameters."""
    text = "a" * 5000
    chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Verify all chunks respect size limit
    assert all(len(chunk) <= chunk_size for chunk in chunks)
```

### Testing Exceptions

```python
"""Tests for error handling."""

import pytest
from green_gov_rag.rag.vector_store import VectorStoreFactory, VectorStoreError


def test_vector_store_factory_raises_on_invalid_type():
    """Test that factory raises error for invalid store type."""
    with pytest.raises(ValueError, match="Unsupported vector store type"):
        VectorStoreFactory.create(store_type="invalid")


def test_query_raises_on_empty_query():
    """Test that empty query raises appropriate error."""
    from green_gov_rag.api.routes.query import query_endpoint

    with pytest.raises(ValueError) as exc_info:
        query_endpoint(query="")

    assert "Query cannot be empty" in str(exc_info.value)


def test_database_connection_error_handling(monkeypatch):
    """Test handling of database connection errors."""
    from green_gov_rag.models.database import get_session

    def mock_failing_connection():
        raise ConnectionError("Database unavailable")

    monkeypatch.setattr("green_gov_rag.models.database.engine.connect", mock_failing_connection)

    with pytest.raises(ConnectionError):
        session = get_session()
```

## Writing Integration Tests

Integration tests verify interactions between components.

### Database Integration Tests

```python
"""Integration tests for database operations."""

import pytest
from sqlmodel import Session, select

from green_gov_rag.models.database import engine, create_db_and_tables
from green_gov_rag.models.document import Document


@pytest.fixture(scope="function")
def test_db():
    """Create test database for each test."""
    create_db_and_tables()
    yield
    # Cleanup after test
    Document.metadata.drop_all(engine)


@pytest.mark.integration
def test_document_crud_operations(test_db):
    """Test create, read, update, delete operations."""
    with Session(engine) as session:
        # Create
        doc = Document(
            title="Test Document",
            content="Test content",
            source_url="https://example.com",
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        assert doc.id is not None

        # Read
        retrieved = session.get(Document, doc.id)
        assert retrieved.title == "Test Document"

        # Update
        retrieved.title = "Updated Title"
        session.commit()

        # Verify update
        updated = session.get(Document, doc.id)
        assert updated.title == "Updated Title"

        # Delete
        session.delete(updated)
        session.commit()

        # Verify deletion
        deleted = session.get(Document, doc.id)
        assert deleted is None
```

### API Integration Tests

```python
"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from green_gov_rag.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.integration
def test_query_endpoint_integration(client):
    """Test query endpoint with real components."""
    response = client.post(
        "/api/query",
        json={
            "query": "What are the EPBC Act requirements?",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) <= 5


@pytest.mark.integration
def test_document_list_endpoint(client):
    """Test document listing endpoint."""
    response = client.get("/api/documents")

    assert response.status_code == 200
    data = response.json()

    assert "documents" in data
    assert isinstance(data["documents"], list)
```

### Vector Store Integration Tests

```python
"""Integration tests for vector store."""

import pytest
from green_gov_rag.rag.vector_store import VectorStoreFactory
from green_gov_rag.rag.embeddings import get_embeddings


@pytest.fixture
def vector_store():
    """Create test vector store."""
    embeddings = get_embeddings()
    store = VectorStoreFactory.create(store_type="faiss")
    return store


@pytest.mark.integration
@pytest.mark.slow
def test_vector_store_similarity_search(vector_store):
    """Test vector similarity search."""
    # Add test documents
    texts = [
        "The EPBC Act protects threatened species.",
        "Native vegetation clearing requires approval.",
        "Environmental impact assessments are mandatory.",
    ]
    vector_store.add_texts(texts)

    # Search
    results = vector_store.similarity_search(
        "How to protect endangered animals?",
        k=2,
    )

    assert len(results) == 2
    assert "EPBC Act" in results[0].page_content
```

## Test Markers

We use pytest markers to categorize tests.

### Available Markers

Defined in `backend/pyproject.toml`:

```python
# Unit tests (default, fast)
@pytest.mark.unit
def test_something():
    pass

# Integration tests (require services)
@pytest.mark.integration
def test_database_integration():
    pass

# Slow tests (take >1 second)
@pytest.mark.slow
def test_large_document_processing():
    pass

# End-to-end tests
@pytest.mark.e2e
def test_complete_workflow():
    pass
```

### Using Markers

```python
"""Example test file with markers."""

import pytest


@pytest.mark.unit
def test_fast_unit_test():
    """Fast unit test."""
    assert 1 + 1 == 2


@pytest.mark.integration
def test_database_integration():
    """Integration test requiring database."""
    # Test with database
    pass


@pytest.mark.slow
@pytest.mark.integration
def test_slow_integration():
    """Slow integration test."""
    # Long-running integration test
    pass


@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature():
    """Test for future feature."""
    pass


@pytest.mark.skipif(
    condition=not has_gpu(),
    reason="Requires GPU",
)
def test_gpu_acceleration():
    """Test GPU-accelerated processing."""
    pass
```

## Mocking and Fixtures

### Common Fixtures

Defined in `tests/conftest.py`:

```python
"""Shared test fixtures."""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path


@pytest.fixture
def sample_document():
    """Provide sample document for testing."""
    return {
        "title": "Test Document",
        "content": "Test content",
        "source_url": "https://example.com",
        "document_type": "regulation",
    }


@pytest.fixture
def sample_documents():
    """Provide list of sample documents."""
    return [
        {"title": f"Document {i}", "content": f"Content {i}"}
        for i in range(5)
    ]


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = Mock()
    llm.invoke.return_value = "Mocked LLM response"
    return llm


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    store = MagicMock()
    store.similarity_search.return_value = [
        Mock(page_content="Test document 1"),
        Mock(page_content="Test document 2"),
    ]
    return store


@pytest.fixture
def temp_test_file(tmp_path):
    """Create temporary test file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    return test_file
```

### Using Fixtures

```python
"""Tests using fixtures."""

import pytest


def test_with_sample_document(sample_document):
    """Test using sample document fixture."""
    assert sample_document["title"] == "Test Document"


def test_with_mock_llm(mock_llm):
    """Test using mocked LLM."""
    response = mock_llm.invoke("Test query")

    assert response == "Mocked LLM response"
    mock_llm.invoke.assert_called_once_with("Test query")


def test_with_temp_file(temp_test_file):
    """Test using temporary file."""
    content = temp_test_file.read_text()

    assert content == "Test content"
```

### Mocking External Services

```python
"""Tests mocking external services."""

import pytest
from unittest.mock import patch, Mock


@patch("green_gov_rag.rag.llm_factory.OpenAI")
def test_query_with_mocked_openai(mock_openai):
    """Test query endpoint with mocked OpenAI."""
    # Configure mock
    mock_instance = Mock()
    mock_instance.invoke.return_value = "Mocked response"
    mock_openai.return_value = mock_instance

    # Test code that uses OpenAI
    from green_gov_rag.rag.enhanced_response import EnhancedRAGPipeline

    pipeline = EnhancedRAGPipeline()
    result = pipeline.query("Test question")

    assert "Mocked response" in result


@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests library."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}

    def mock_get(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("requests.get", mock_get)
    return mock_response


def test_document_scraper_with_mocked_requests(mock_requests):
    """Test scraper with mocked HTTP requests."""
    from green_gov_rag.etl.sources.epbc_scraper import EPBCScraper

    scraper = EPBCScraper()
    documents = scraper.fetch_documents()

    # Verify mocked request was used
    assert len(documents) > 0
```

## Code Coverage

### Coverage Requirements

- **Minimum overall**: 70%
- **Core RAG logic**: 90%+
- **API endpoints**: 80%+
- **ETL pipeline**: 80%+
- **Utilities**: 70%+

### Checking Coverage

```bash
# Generate coverage report
pytest --cov=green_gov_rag --cov-report=html

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Show coverage in terminal
pytest --cov=green_gov_rag --cov-report=term-missing

# Check coverage for specific module
pytest --cov=green_gov_rag.rag --cov-report=term

# Fail if coverage below threshold
pytest --cov=green_gov_rag --cov-fail-under=70
```

### Coverage Configuration

In `backend/pyproject.toml`:

```toml
[tool.coverage.run]
source = ["green_gov_rag"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/site-packages/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise AssertionError",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

### Improving Coverage

```python
# Mark code that shouldn't be covered
def debug_only_function():  # pragma: no cover
    """Only used for debugging."""
    print("Debug info")


# Cover edge cases
def test_all_branches():
    """Test all code branches."""
    # Test happy path
    result = function(valid_input)
    assert result.success

    # Test error cases
    with pytest.raises(ValueError):
        function(invalid_input)

    # Test edge cases
    result = function(edge_case_input)
    assert result.handled_correctly
```

## Testing Best Practices

### 1. Arrange-Act-Assert Pattern

```python
def test_document_processing():
    """Test document processing."""
    # Arrange - Set up test data
    document = create_test_document()
    processor = DocumentProcessor(chunk_size=1000)

    # Act - Execute the code being tested
    result = processor.process(document)

    # Assert - Verify the results
    assert len(result.chunks) > 0
    assert result.metadata["processed"] is True
```

### 2. Test One Thing at a Time

```python
# Good: Single responsibility
def test_chunker_respects_size_limit():
    """Test that chunker respects size limit."""
    text = "a" * 5000
    chunks = chunk_text(text, chunk_size=1000)

    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_chunker_maintains_overlap():
    """Test that chunker maintains overlap."""
    text = "abcd" * 500
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100)

    overlap = chunks[0][-100:]
    assert overlap == chunks[1][:100]


# Bad: Testing multiple things
def test_chunker():
    """Test chunker."""
    # Tests size, overlap, edge cases all at once
    # Hard to debug when it fails
    pass
```

### 3. Use Descriptive Names

```python
# Good: Clear what's being tested
def test_query_endpoint_returns_404_when_document_not_found():
    pass


# Bad: Unclear
def test_query():
    pass
```

### 4. Avoid Test Interdependence

```python
# Bad: Tests depend on each other
class TestDocumentProcessor:
    document = None

    def test_create_document(self):
        self.document = create_document()
        assert self.document

    def test_process_document(self):
        # Depends on test_create_document running first
        process(self.document)


# Good: Independent tests
class TestDocumentProcessor:
    def test_create_document(self):
        document = create_document()
        assert document

    def test_process_document(self):
        document = create_document()  # Set up own test data
        result = process(document)
        assert result
```

### 5. Clean Up Resources

```python
# Good: Using fixtures for cleanup
@pytest.fixture
def temp_database():
    """Create temporary database."""
    db = create_test_db()
    yield db
    db.cleanup()  # Automatic cleanup


def test_with_database(temp_database):
    # Database automatically cleaned up after test
    pass
```

## CI/CD Testing

### GitHub Actions Workflow

Tests run automatically on push and pull requests:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd backend
          pip install -e .[dev]
      - name: Run tests
        run: |
          cd backend
          pytest --cov=green_gov_rag --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Local CI Simulation

```bash
# Run same checks as CI
cd backend

# Format check
ruff format --check .

# Lint check
ruff check .

# Type check
mypy green_gov_rag tests

# Tests with coverage
pytest --cov=green_gov_rag --cov-report=xml --cov-fail-under=70
```

## Debugging Tests

### Running in Debug Mode

```python
# Add pytest.set_trace() for debugging
def test_complex_logic():
    """Test complex logic."""
    result = complex_function()

    import pytest; pytest.set_trace()  # Debugger will stop here

    assert result.is_valid
```

### VS Code Debugging

1. Set breakpoint in test file
2. Press F5 or use Debug panel
3. Select "Python: Pytest" configuration

### Print Debugging

```bash
# Show print statements
pytest -s

# Show very verbose output
pytest -vv

# Show local variables on failure
pytest --showlocals
```

### Debugging Failures

```bash
# Show full traceback
pytest --tb=long

# Show only failed test output
pytest --tb=short

# Show minimal output
pytest --tb=line
```

---

**Next step:** Learn how to submit your changes with the [Pull Request Guide](pull-requests.md)!
