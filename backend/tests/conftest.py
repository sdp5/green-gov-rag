"""Pytest configuration and shared fixtures for testing."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# =============================================================================
# Mock External Services
# =============================================================================


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("CLOUD_PROVIDER", "local")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "test-connection-string")


@pytest.fixture()
def reload_settings(monkeypatch):
    """Fixture to reload settings after monkeypatching environment variables.

    Usage:
        def test_something(monkeypatch, reload_settings):
            monkeypatch.setenv("CLOUD_PROVIDER", "azure")
            new_settings = reload_settings()
            # new_settings will have the updated values
    """

    def _reload():
        from green_gov_rag.config import Settings

        return Settings()

    return _reload


@pytest.fixture()
def mock_openai_embeddings():
    """Mock OpenAI embeddings API."""
    with patch("langchain_community.embeddings.OpenAIEmbeddings") as mock:
        mock_instance = Mock()
        mock_instance.embed_query.return_value = [0.1] * 384  # Mock 384-dim embedding
        mock_instance.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]
        mock.return_value = mock_instance
        yield mock


@pytest.fixture()
def mock_huggingface_embeddings():
    """Mock HuggingFace embeddings."""
    with patch("langchain_community.embeddings.HuggingFaceEmbeddings") as mock:
        mock_instance = Mock()
        mock_instance.embed_query.return_value = [0.1] * 384
        mock_instance.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]
        mock.return_value = mock_instance
        yield mock


@pytest.fixture()
def mock_bedrock_embeddings():
    """Mock AWS Bedrock embeddings."""
    with patch("boto3.client") as mock_boto:
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            "body": Mock(read=lambda: b'{"embedding": [0.1, 0.2, 0.3]}'),
        }
        mock_boto.return_value = mock_bedrock
        yield mock_boto


@pytest.fixture()
def mock_openai_chat():
    """Mock OpenAI chat completions API."""
    with patch("openai.ChatCompletion.create") as mock:
        mock.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is a test response from the mocked LLM."
                    }
                },
            ],
        }
        yield mock


@pytest.fixture()
def mock_s3_client():
    """Mock AWS S3 client."""
    with patch("boto3.client") as mock_boto:
        mock_s3 = Mock()
        mock_s3.upload_file.return_value = None
        mock_s3.download_file.return_value = None
        mock_s3.list_objects_v2.return_value = {"Contents": []}
        mock_s3.delete_object.return_value = None
        mock_s3.head_object.return_value = {"ContentLength": 100}
        mock_boto.return_value = mock_s3
        yield mock_s3


@pytest.fixture()
def mock_azure_blob():
    """Mock Azure Blob Storage client."""
    with patch("azure.storage.blob.BlobServiceClient") as mock:
        mock_instance = Mock()
        mock_container = Mock()
        mock_blob = Mock()

        mock_blob.upload_blob.return_value = None
        mock_blob.download_blob.return_value = Mock(readall=lambda: b"test content")
        mock_blob.exists.return_value = True
        mock_blob.delete_blob.return_value = None

        mock_container.get_blob_client.return_value = mock_blob
        mock_container.list_blobs.return_value = []

        mock_instance.get_container_client.return_value = mock_container
        mock.from_connection_string.return_value = mock_instance

        yield mock


# =============================================================================
# Test Database Fixtures
# =============================================================================


@pytest.fixture()
def temp_vector_store():
    """Create a temporary FAISS vector store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "test_faiss.index"
        yield store_path


@pytest.fixture()
def in_memory_faiss():
    """Create an in-memory FAISS index for testing."""
    from langchain.schema import Document
    from langchain_community.vectorstores import FAISS
    from langchain_core.embeddings import Embeddings

    # Create a simple mock embeddings function
    class MockEmbeddings(Embeddings):
        def embed_documents(self, texts):
            return [[0.1] * 384 for _ in texts]

        def embed_query(self, text):
            return [0.1] * 384

    mock_embeddings = MockEmbeddings()

    # Create sample documents
    documents = [
        Document(page_content="Carbon emissions report", metadata={"region": "NSW"}),
        Document(page_content="Biodiversity guidelines", metadata={"region": "SA"}),
    ]

    # Build FAISS index in memory
    vector_store = FAISS.from_documents(documents, mock_embeddings)
    yield vector_store


@pytest.fixture()
def test_db_path():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture()
def mock_postgres_connection():
    """Mock PostgreSQL connection for testing."""
    with patch("psycopg2.connect") as mock_connect:
        mock_conn = Mock()
        mock_cursor = Mock()

        # Mock cursor operations
        mock_cursor.execute.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None

        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_conn.close.return_value = None

        mock_connect.return_value = mock_conn
        yield mock_conn


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture()
def sample_chunks():
    """Sample document chunks for testing."""
    return [
        {
            "content": "Carbon emissions reporting guidelines for NSW coal mining operations.",
            "metadata": {
                "source": "nsw_emissions.pdf",
                "region": "NSW",
                "topic": "emissions",
                "page": 1,
            },
        },
        {
            "content": "Biodiversity conservation requirements for South Australia.",
            "metadata": {
                "source": "sa_biodiversity.pdf",
                "region": "SA",
                "topic": "biodiversity",
                "page": 1,
            },
        },
        {
            "content": "Water usage regulations for agricultural operations in Victoria.",
            "metadata": {
                "source": "vic_water.pdf",
                "region": "VIC",
                "topic": "water",
                "page": 1,
            },
        },
    ]


@pytest.fixture()
def sample_documents():
    """Sample document metadata for testing."""
    return [
        {
            "title": "NSW Emissions Guidelines",
            "jurisdiction": "NSW",
            "topic": "emissions",
            "download_urls": ["https://example.com/nsw_emissions.pdf"],
        },
        {
            "title": "SA Biodiversity Policy",
            "jurisdiction": "SA",
            "topic": "biodiversity",
            "download_urls": ["https://example.com/sa_biodiversity.pdf"],
        },
    ]


@pytest.fixture()
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        (data_dir / "raw").mkdir()
        (data_dir / "processed").mkdir()
        (data_dir / "chunks").mkdir()
        yield data_dir


# =============================================================================
# Mock Embeddings and Vector Store
# =============================================================================


class MockChunkEmbedder:
    """Mock embedder for testing without external API calls."""

    def __init__(self, provider: str = "mock", model_name: str | None = None):
        self.provider = provider
        self.model_name = model_name or "mock-embeddings-model"
        self.embedding_dim = 384

    def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        """Generate mock embeddings for chunks."""
        embedded = []
        for _i, chunk in enumerate(chunks):
            # Create deterministic embeddings based on content hash
            embedding = [
                hash(chunk.get("content", "")) % 1000 / 1000.0,
            ] * self.embedding_dim
            embedded.append(
                {
                    "content": chunk.get("content"),
                    "metadata": chunk.get("metadata", {}),
                    "embedding": embedding,
                },
            )
        return embedded

    def embed_query(self, text: str) -> list[float]:
        """Generate mock embedding for a query."""
        return [hash(text) % 1000 / 1000.0] * self.embedding_dim


@pytest.fixture()
def mock_embedder():
    """Provide a mock embedder that doesn't call external APIs."""
    return MockChunkEmbedder()


# =============================================================================
# Auto-use Fixtures for All Tests
# =============================================================================


@pytest.fixture(autouse=True)
def disable_external_requests(monkeypatch):
    """Prevent accidental external API calls during tests."""
    # Mock requests to prevent actual HTTP calls
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"mock content"
        mock_response.text = "mock content"
        mock_response.json.return_value = {}

        mock_get.return_value = mock_response
        mock_post.return_value = mock_response

        yield


@pytest.fixture(autouse=True)
def clean_import_cache():
    """Clean import cache between tests to ensure isolation."""
    import sys

    before = set(sys.modules.keys())
    yield
    # Don't remove pytest or core modules
    after = set(sys.modules.keys())
    to_remove = after - before
    for module in to_remove:
        if not module.startswith(("_pytest", "pytest", "py.")):
            sys.modules.pop(module, None)
