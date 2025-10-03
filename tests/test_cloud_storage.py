"""Tests for cloud storage abstraction layer."""

import os
from io import BytesIO
from pathlib import Path

import pytest

from green_gov_rag.cloud.storage import LocalBackend, StorageClient


class TestLocalBackend:
    """Test local storage backend."""

    @pytest.fixture()
    def temp_storage_path(self, tmp_path: Path) -> Path:
        """Create temporary storage path."""
        return tmp_path / "storage"

    @pytest.fixture()
    def backend(self, temp_storage_path: Path) -> LocalBackend:
        """Create local backend instance."""
        return LocalBackend(base_path=temp_storage_path)

    def test_upload_and_download_file(self, backend: LocalBackend, tmp_path: Path) -> None:
        """Test uploading and downloading a file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, cloud storage!"
        test_file.write_text(test_content)

        # Upload
        backend.upload_file(test_file, "test-container", "test.txt")

        # Verify exists
        assert backend.file_exists("test-container", "test.txt")

        # Download
        download_path = tmp_path / "downloaded.txt"
        backend.download_file("test-container", "test.txt", download_path)

        # Verify content
        assert download_path.read_text() == test_content

    def test_upload_and_download_fileobj(self, backend: LocalBackend) -> None:
        """Test uploading and downloading using file objects."""
        # Create content
        content = b"Binary content for testing"
        upload_obj = BytesIO(content)

        # Upload
        backend.upload_fileobj(upload_obj, "test-container", "binary.bin")

        # Verify exists
        assert backend.file_exists("test-container", "binary.bin")

        # Download
        download_obj = BytesIO()
        backend.download_fileobj("test-container", "binary.bin", download_obj)

        # Verify content
        download_obj.seek(0)
        assert download_obj.read() == content

    def test_list_files(self, backend: LocalBackend, tmp_path: Path) -> None:
        """Test listing files with prefix."""
        # Create test files
        test_files = [
            "docs/doc1.txt",
            "docs/doc2.txt",
            "images/img1.png",
        ]

        for file_key in test_files:
            test_file = tmp_path / file_key
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("content")
            backend.upload_file(test_file, "test-container", file_key)

        # List all files
        all_files = backend.list_files("test-container")
        assert len(all_files) == 3

        # List with prefix
        docs_files = backend.list_files("test-container", prefix="docs/")
        assert len(docs_files) == 2
        assert all(f.startswith("docs/") for f in docs_files)

    def test_delete_file(self, backend: LocalBackend, tmp_path: Path) -> None:
        """Test deleting a file."""
        # Create and upload test file
        test_file = tmp_path / "delete_me.txt"
        test_file.write_text("Delete this")
        backend.upload_file(test_file, "test-container", "delete_me.txt")

        # Verify exists
        assert backend.file_exists("test-container", "delete_me.txt")

        # Delete
        backend.delete_file("test-container", "delete_me.txt")

        # Verify deleted
        assert not backend.file_exists("test-container", "delete_me.txt")

    def test_file_exists(self, backend: LocalBackend) -> None:
        """Test file existence check."""
        # Non-existent file
        assert not backend.file_exists("test-container", "nonexistent.txt")


class TestStorageClient:
    """Test StorageClient with different providers."""

    @pytest.fixture()
    def temp_storage_path(self, tmp_path: Path) -> Path:
        """Create temporary storage path."""
        storage_path = tmp_path / "storage"
        storage_path.mkdir()
        return storage_path

    @pytest.fixture(autouse=True)
    def setup_env(self, temp_storage_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set up environment for tests."""
        monkeypatch.setenv("CLOUD_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_STORAGE_PATH", str(temp_storage_path))

    def test_auto_detect_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test automatic provider detection from environment."""
        monkeypatch.setenv("CLOUD_PROVIDER", "local")
        client = StorageClient()
        assert client.provider == "local"

    def test_explicit_provider(self, temp_storage_path: Path) -> None:
        """Test explicitly specifying provider."""
        client = StorageClient(provider="local")
        assert client.provider == "local"

    def test_invalid_provider(self) -> None:
        """Test error on invalid provider."""
        with pytest.raises(ValueError, match="Unsupported cloud provider"):
            StorageClient(provider="invalid")

    def test_storage_operations(self, tmp_path: Path) -> None:
        """Test basic storage operations through client."""
        client = StorageClient(provider="local")

        # Create test file
        test_file = tmp_path / "client_test.txt"
        test_content = "Testing StorageClient"
        test_file.write_text(test_content)

        # Upload
        client.upload_file(test_file, "test-container", "client_test.txt")

        # Check existence
        assert client.file_exists("test-container", "client_test.txt")

        # List files
        files = client.list_files("test-container")
        assert "client_test.txt" in files

        # Download
        download_path = tmp_path / "downloaded_client.txt"
        client.download_file("test-container", "client_test.txt", download_path)
        assert download_path.read_text() == test_content

        # Delete
        client.delete_file("test-container", "client_test.txt")
        assert not client.file_exists("test-container", "client_test.txt")


class TestCloudConfig:
    """Test cloud configuration."""

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading config from environment."""
        from green_gov_rag.cloud.config import CloudConfig

        monkeypatch.setenv("CLOUD_PROVIDER", "azure")
        monkeypatch.setenv("CLOUD_REGION", "australiaeast")
        monkeypatch.setenv("STORAGE_CONTAINER", "my-container")
        monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;...")

        config = CloudConfig.from_env()

        assert config.provider == "azure"
        assert config.region == "australiaeast"
        assert config.storage_container == "my-container"

    def test_validate_invalid_provider(self) -> None:
        """Test validation with invalid provider."""
        from green_gov_rag.cloud.config import CloudConfig

        config = CloudConfig(provider="invalid")

        with pytest.raises(ValueError, match="Invalid CLOUD_PROVIDER"):
            config.validate()

    def test_validate_azure_missing_connection_string(self) -> None:
        """Test validation for Azure without connection string."""
        from green_gov_rag.cloud.config import CloudConfig

        config = CloudConfig(provider="azure", storage_connection_string=None)

        with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING is required"):
            config.validate()


# Integration test (requires mock or actual cloud credentials)
@pytest.mark.skipif(
    os.getenv("RUN_CLOUD_INTEGRATION_TESTS") != "true",
    reason="Cloud integration tests disabled by default",
)
class TestCloudIntegration:
    """Integration tests for actual cloud providers.

    Set RUN_CLOUD_INTEGRATION_TESTS=true to enable.
    Requires valid cloud credentials.
    """

    @pytest.mark.skipif(os.getenv("TEST_AWS") != "true", reason="AWS tests not enabled")
    def test_aws_operations(self, tmp_path: Path) -> None:
        """Test AWS S3 operations."""
        client = StorageClient(provider="aws")
        container = os.getenv("AWS_TEST_BUCKET", "test-greengovrag")

        # Create test file
        test_file = tmp_path / "aws_test.txt"
        test_file.write_text("AWS integration test")

        # Upload
        client.upload_file(test_file, container, "integration/aws_test.txt")

        # Verify
        assert client.file_exists(container, "integration/aws_test.txt")

        # Download
        download_path = tmp_path / "aws_downloaded.txt"
        client.download_file(container, "integration/aws_test.txt", download_path)
        assert download_path.read_text() == "AWS integration test"

        # Cleanup
        client.delete_file(container, "integration/aws_test.txt")

    @pytest.mark.skipif(os.getenv("TEST_AZURE") != "true", reason="Azure tests not enabled")
    def test_azure_operations(self, tmp_path: Path) -> None:
        """Test Azure Blob Storage operations."""
        client = StorageClient(provider="azure")
        container = os.getenv("AZURE_TEST_CONTAINER", "test-greengovrag")

        # Create test file
        test_file = tmp_path / "azure_test.txt"
        test_file.write_text("Azure integration test")

        # Upload
        client.upload_file(test_file, container, "integration/azure_test.txt")

        # Verify
        assert client.file_exists(container, "integration/azure_test.txt")

        # Download
        download_path = tmp_path / "azure_downloaded.txt"
        client.download_file(container, "integration/azure_test.txt", download_path)
        assert download_path.read_text() == "Azure integration test"

        # Cleanup
        client.delete_file(container, "integration/azure_test.txt")
