"""Cloud-agnostic storage abstraction layer for GreenGovRAG.

Supports AWS S3, Azure Blob Storage, and local filesystem storage.
Provider is selected via CLOUD_PROVIDER environment variable.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional, Union


class StorageBackend(ABC):
    """Abstract base class for cloud storage backends."""

    @abstractmethod
    def upload_file(self, local_path: Union[str, Path], container: str, key: str) -> None:
        """Upload a file to cloud storage.

        Args:
            local_path: Path to local file
            container: Bucket/container name
            key: Object key/path in storage
        """

    @abstractmethod
    def download_file(self, container: str, key: str, local_path: Union[str, Path]) -> None:
        """Download a file from cloud storage.

        Args:
            container: Bucket/container name
            key: Object key/path in storage
            local_path: Path where to save the file
        """

    @abstractmethod
    def upload_fileobj(self, fileobj: BinaryIO, container: str, key: str) -> None:
        """Upload a file-like object to cloud storage.

        Args:
            fileobj: File-like object to upload
            container: Bucket/container name
            key: Object key/path in storage
        """

    @abstractmethod
    def download_fileobj(self, container: str, key: str, fileobj: BinaryIO) -> None:
        """Download a file to a file-like object.

        Args:
            container: Bucket/container name
            key: Object key/path in storage
            fileobj: File-like object to write to
        """

    @abstractmethod
    def list_files(self, container: str, prefix: str = "") -> list[str]:
        """List files in a container with optional prefix.

        Args:
            container: Bucket/container name
            prefix: Optional prefix to filter files

        Returns:
            List of file keys
        """

    @abstractmethod
    def delete_file(self, container: str, key: str) -> None:
        """Delete a file from cloud storage.

        Args:
            container: Bucket/container name
            key: Object key/path in storage
        """

    @abstractmethod
    def file_exists(self, container: str, key: str) -> bool:
        """Check if a file exists in cloud storage.

        Args:
            container: Bucket/container name
            key: Object key/path in storage

        Returns:
            True if file exists, False otherwise
        """


class AWSBackend(StorageBackend):
    """AWS S3 storage backend."""

    def __init__(self) -> None:
        """Initialize AWS S3 client."""
        try:
            import boto3
        except ImportError as e:
            msg = "boto3 is required for AWS backend. Install with: pip install boto3"
            raise ImportError(msg) from e

        self.s3 = boto3.client("s3")

    def upload_file(self, local_path: Union[str, Path], container: str, key: str) -> None:
        """Upload a file to S3."""
        self.s3.upload_file(str(local_path), container, key)

    def download_file(self, container: str, key: str, local_path: Union[str, Path]) -> None:
        """Download a file from S3."""
        self.s3.download_file(container, key, str(local_path))

    def upload_fileobj(self, fileobj: BinaryIO, container: str, key: str) -> None:
        """Upload a file-like object to S3."""
        self.s3.upload_fileobj(fileobj, container, key)

    def download_fileobj(self, container: str, key: str, fileobj: BinaryIO) -> None:
        """Download a file from S3 to a file-like object."""
        self.s3.download_fileobj(container, key, fileobj)

    def list_files(self, container: str, prefix: str = "") -> list[str]:
        """List files in S3 bucket."""
        response = self.s3.list_objects_v2(Bucket=container, Prefix=prefix)
        return [obj["Key"] for obj in response.get("Contents", [])]

    def delete_file(self, container: str, key: str) -> None:
        """Delete a file from S3."""
        self.s3.delete_object(Bucket=container, Key=key)

    def file_exists(self, container: str, key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self.s3.head_object(Bucket=container, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False


class AzureBackend(StorageBackend):
    """Azure Blob Storage backend."""

    def __init__(self) -> None:
        """Initialize Azure Blob Storage client."""
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as e:
            msg = "azure-storage-blob is required for Azure backend. Install with: pip install azure-storage-blob"
            raise ImportError(msg) from e

        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            msg = "AZURE_STORAGE_CONNECTION_STRING environment variable is required"
            raise ValueError(msg)

        self.blob_service = BlobServiceClient.from_connection_string(conn_str)

    def upload_file(self, local_path: Union[str, Path], container: str, key: str) -> None:
        """Upload a file to Azure Blob Storage."""
        blob_client = self.blob_service.get_blob_client(container, key)
        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

    def download_file(self, container: str, key: str, local_path: Union[str, Path]) -> None:
        """Download a file from Azure Blob Storage."""
        blob_client = self.blob_service.get_blob_client(container, key)
        with open(local_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())

    def upload_fileobj(self, fileobj: BinaryIO, container: str, key: str) -> None:
        """Upload a file-like object to Azure Blob Storage."""
        blob_client = self.blob_service.get_blob_client(container, key)
        blob_client.upload_blob(fileobj, overwrite=True)

    def download_fileobj(self, container: str, key: str, fileobj: BinaryIO) -> None:
        """Download a file from Azure Blob Storage to a file-like object."""
        blob_client = self.blob_service.get_blob_client(container, key)
        fileobj.write(blob_client.download_blob().readall())

    def list_files(self, container: str, prefix: str = "") -> list[str]:
        """List files in Azure container."""
        container_client = self.blob_service.get_container_client(container)
        return [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]

    def delete_file(self, container: str, key: str) -> None:
        """Delete a file from Azure Blob Storage."""
        blob_client = self.blob_service.get_blob_client(container, key)
        blob_client.delete_blob()

    def file_exists(self, container: str, key: str) -> bool:
        """Check if a file exists in Azure Blob Storage."""
        blob_client = self.blob_service.get_blob_client(container, key)
        return blob_client.exists()


class LocalBackend(StorageBackend):
    """Local filesystem storage backend for development and testing."""

    def __init__(self, base_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize local storage backend.

        Args:
            base_path: Base directory for storage. Defaults to ./data/storage
        """
        self.base_path = Path(base_path) if base_path else Path("./data/storage")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, container: str, key: str) -> Path:
        """Get full local path for a container and key."""
        full_path = self.base_path / container / key
        return full_path

    def upload_file(self, local_path: Union[str, Path], container: str, key: str) -> None:
        """Copy a file to local storage."""
        dest = self._get_full_path(container, key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copy2(local_path, dest)

    def download_file(self, container: str, key: str, local_path: Union[str, Path]) -> None:
        """Copy a file from local storage."""
        src = self._get_full_path(container, key)

        import shutil

        shutil.copy2(src, local_path)

    def upload_fileobj(self, fileobj: BinaryIO, container: str, key: str) -> None:
        """Write a file-like object to local storage."""
        dest = self._get_full_path(container, key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            f.write(fileobj.read())

    def download_fileobj(self, container: str, key: str, fileobj: BinaryIO) -> None:
        """Read a file from local storage to a file-like object."""
        src = self._get_full_path(container, key)
        with open(src, "rb") as f:
            fileobj.write(f.read())

    def list_files(self, container: str, prefix: str = "") -> list[str]:
        """List files in local storage container."""
        container_path = self.base_path / container
        if not container_path.exists():
            return []

        prefix_path = container_path / prefix if prefix else container_path
        if prefix_path.is_file():
            return [prefix]

        all_files = []
        for file_path in prefix_path.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(container_path)
                all_files.append(str(relative))
        return all_files

    def delete_file(self, container: str, key: str) -> None:
        """Delete a file from local storage."""
        file_path = self._get_full_path(container, key)
        if file_path.exists():
            file_path.unlink()

    def file_exists(self, container: str, key: str) -> bool:
        """Check if a file exists in local storage."""
        return self._get_full_path(container, key).exists()


class StorageClient:
    """Cloud-agnostic storage client.

    Automatically selects the appropriate backend based on the
    CLOUD_PROVIDER environment variable.

    Supported providers:
    - aws: Amazon S3
    - azure: Azure Blob Storage
    - local: Local filesystem (default for development)
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        """Initialize storage client.

        Args:
            provider: Cloud provider ('aws', 'azure', 'local').
                     If None, reads from CLOUD_PROVIDER env var (defaults to 'local')
        """
        self.provider = provider or os.getenv("CLOUD_PROVIDER", "local")

        if self.provider == "aws":
            self.backend: StorageBackend = AWSBackend()
        elif self.provider == "azure":
            self.backend = AzureBackend()
        elif self.provider == "local":
            base_path = os.getenv("LOCAL_STORAGE_PATH", "./data/storage")
            self.backend = LocalBackend(base_path=base_path)
        else:
            msg = f"Unsupported cloud provider: {self.provider}. Use 'aws', 'azure', or 'local'"
            raise ValueError(msg)

    def upload_file(self, local_path: Union[str, Path], container: str, key: str) -> None:
        """Upload a file to cloud storage.

        Args:
            local_path: Path to local file
            container: Bucket/container name
            key: Object key/path in storage
        """
        self.backend.upload_file(local_path, container, key)

    def download_file(self, container: str, key: str, local_path: Union[str, Path]) -> None:
        """Download a file from cloud storage.

        Args:
            container: Bucket/container name
            key: Object key/path in storage
            local_path: Path where to save the file
        """
        self.backend.download_file(container, key, local_path)

    def upload_fileobj(self, fileobj: BinaryIO, container: str, key: str) -> None:
        """Upload a file-like object to cloud storage.

        Args:
            fileobj: File-like object to upload
            container: Bucket/container name
            key: Object key/path in storage
        """
        self.backend.upload_fileobj(fileobj, container, key)

    def download_fileobj(self, container: str, key: str, fileobj: BinaryIO) -> None:
        """Download a file to a file-like object.

        Args:
            container: Bucket/container name
            key: Object key/path in storage
            fileobj: File-like object to write to
        """
        self.backend.download_fileobj(container, key, fileobj)

    def list_files(self, container: str, prefix: str = "") -> list[str]:
        """List files in a container with optional prefix.

        Args:
            container: Bucket/container name
            prefix: Optional prefix to filter files

        Returns:
            List of file keys
        """
        return self.backend.list_files(container, prefix)

    def delete_file(self, container: str, key: str) -> None:
        """Delete a file from cloud storage.

        Args:
            container: Bucket/container name
            key: Object key/path in storage
        """
        self.backend.delete_file(container, key)

    def file_exists(self, container: str, key: str) -> bool:
        """Check if a file exists in cloud storage.

        Args:
            container: Bucket/container name
            key: Object key/path in storage

        Returns:
            True if file exists, False otherwise
        """
        return self.backend.file_exists(container, key)
