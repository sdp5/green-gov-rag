"""ETL Storage Adapter - Cloud-agnostic storage layer for ETL pipeline.

Provides high-level storage operations for document ingestion, processing,
and chunk storage across local filesystem, AWS S3, and Azure Blob Storage.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from green_gov_rag.cloud.storage import StorageClient
from green_gov_rag.config import settings
from green_gov_rag.types import DEFAULT_HTTP_HEADERS

logger = logging.getLogger(__name__)


class ETLStorageAdapter:
    """High-level storage adapter for ETL pipeline operations.

    Provides a unified interface for document and chunk storage operations
    across different cloud providers (AWS S3, Azure Blob, local filesystem).

    All paths use a consistent structure (matching local mode):
    - Documents: {container}/documents/{jurisdiction}/{category}/{topic}/{filename}
    - Metadata: {container}/documents/{jurisdiction}/{category}/{topic}/{filename}.metadata.json
    - Chunks: {container}/chunks/{document_id}/{chunk_id}.json
    """

    def __init__(self, provider: str | None = None, container: str | None = None):
        """Initialize ETL storage adapter.

        Args:
            provider: Cloud provider ('local', 'aws', 'azure'). Defaults to settings.
            container: Storage container/bucket name. Defaults to settings.
        """
        self.storage = StorageClient(provider=provider)
        self.container = container or settings.storage_container
        self.provider = provider or settings.cloud_provider

        logger.info(
            f"Initialized ETL storage adapter: provider={self.provider}, "
            f"container={self.container}"
        )

    def _generate_document_id(self, url: str, title: str) -> str:
        """Generate unique document ID from URL and title.

        Args:
            url: Source URL
            title: Document title

        Returns:
            MD5 hash as document ID
        """
        content = f"{url}::{title}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _build_document_path(
        self,
        jurisdiction: str,
        category: str,
        topic: str,
        filename: str,
    ) -> str:
        """Build storage path for a document.

        Args:
            jurisdiction: Document jurisdiction (federal/state/local)
            category: Document category
            topic: Document topic
            filename: Document filename

        Returns:
            Storage path
        """
        # Sanitize path components
        jurisdiction = jurisdiction.replace(" ", "_").lower()
        category = category.replace(" ", "_").lower()
        topic = topic.replace(" ", "_").lower()

        return f"documents/{jurisdiction}/{category}/{topic}/{filename}"

    def _build_metadata_path(
        self,
        jurisdiction: str,
        category: str,
        topic: str,
        filename: str,
    ) -> str:
        """Build storage path for document metadata.

        Args:
            jurisdiction: Document jurisdiction
            category: Document category
            topic: Document topic
            filename: Document filename

        Returns:
            Metadata storage path
        """
        # Sanitize path components
        jurisdiction = jurisdiction.replace(" ", "_").lower()
        category = category.replace(" ", "_").lower()
        topic = topic.replace(" ", "_").lower()

        # Store metadata alongside documents (consistent with local mode)
        return f"documents/{jurisdiction}/{category}/{topic}/{filename}.metadata.json"

    def download_from_url(
        self,
        url: str,
        metadata: dict[str, Any],
        retries: int = 3,
        backoff: int = 2,
    ) -> str:
        """Download file from URL and store in cloud storage.

        Args:
            url: URL to download from
            metadata: Document metadata (title, jurisdiction, category, topic)
            retries: Number of retry attempts
            backoff: Backoff multiplier for retries

        Returns:
            Document ID

        Raises:
            RuntimeError: If download fails after all retries
        """
        import time

        title = metadata.get("title", "untitled")
        jurisdiction = metadata.get("jurisdiction", "unknown")
        category = metadata.get("category", "misc")
        topic = metadata.get("topic", "general")

        # Extract filename from URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        filename = Path(parsed.path).name or "downloaded_file"

        # Build storage paths
        doc_path = self._build_document_path(jurisdiction, category, topic, filename)
        meta_path = self._build_metadata_path(jurisdiction, category, topic, filename)

        # Check if already exists
        if self.storage.file_exists(self.container, doc_path):
            logger.info(f"Document already exists: {doc_path}")
            doc_id = self._generate_document_id(url, title)
            return doc_id

        # Download with retries (using browser-like headers to avoid bot detection)
        attempt = 0
        last_error: Exception | None = None
        last_status_code = None

        while attempt < retries:
            try:
                logger.info(f"Downloading {url} (attempt {attempt + 1}/{retries})")
                response = requests.get(
                    url,
                    timeout=30,
                    headers=DEFAULT_HTTP_HEADERS,
                    allow_redirects=True,
                )
                last_status_code = response.status_code

                # Check for bot protection (403/503 from Cloudflare, etc.)
                if response.status_code in (403, 503):
                    # Check if it's Cloudflare protection
                    is_cloudflare = (
                        "cloudflare" in response.headers.get("Server", "").lower()
                        or "cf-ray" in response.headers
                        or "cf-mitigated" in response.headers
                    )
                    if is_cloudflare:
                        logger.warning(
                            f"Cloudflare protection detected for {url}. "
                            "Manual download required."
                        )
                        msg = (
                            f"Cloudflare bot protection blocking access to {url}. "
                            "Please download manually or use alternative methods."
                        )
                        raise RuntimeError(msg)

                response.raise_for_status()

                # Upload document to storage
                from io import BytesIO

                file_obj = BytesIO(response.content)
                self.storage.upload_fileobj(file_obj, self.container, doc_path)

                # Generate document ID and add to metadata
                doc_id = self._generate_document_id(url, title)
                enriched_metadata = {
                    **metadata,
                    "document_id": doc_id,
                    "source_url": url,
                    "filename": filename,
                    "download_timestamp": datetime.utcnow().isoformat(),
                    "storage_path": doc_path,
                    "storage_provider": self.provider,
                    "sha256": hashlib.sha256(response.content).hexdigest(),
                    "size_bytes": len(response.content),
                }

                # Save metadata
                self.save_metadata(doc_id, enriched_metadata, meta_path)

                logger.info(f"Successfully downloaded and stored: {doc_path}")
                return doc_id

            except requests.exceptions.HTTPError as e:
                last_error = e
                attempt += 1

                # Don't retry on 403/401 - likely bot protection
                if last_status_code in (403, 401):
                    logger.error(
                        f"Access denied (HTTP {last_status_code}) for {url}. "
                        "Likely bot protection or authentication required."
                    )
                    break

                logger.warning(
                    f"HTTP error on attempt {attempt} for {url}: {e}",
                    exc_info=True,
                )
                if attempt < retries:
                    time.sleep(backoff**attempt)

            except Exception as e:
                last_error = e
                attempt += 1
                logger.warning(
                    f"Download attempt {attempt} failed for {url}: {e}",
                    exc_info=True,
                )
                if attempt < retries:
                    time.sleep(backoff**attempt)

        # All retries failed
        msg = f"Failed to download {url} after {retries} attempts: {last_error}"
        raise RuntimeError(msg)

    def save_document(
        self,
        content: bytes | str,
        metadata: dict[str, Any],
    ) -> str:
        """Save document content and metadata to storage.

        Args:
            content: Document content (bytes or string)
            metadata: Document metadata

        Returns:
            Document ID
        """
        jurisdiction = metadata.get("jurisdiction", "unknown")
        category = metadata.get("category", "misc")
        topic = metadata.get("topic", "general")
        filename = metadata.get("filename", "document")

        # Build storage paths
        doc_path = self._build_document_path(jurisdiction, category, topic, filename)
        meta_path = self._build_metadata_path(jurisdiction, category, topic, filename)

        # Convert content to bytes if string
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        # Upload document
        from io import BytesIO

        file_obj = BytesIO(content_bytes)
        self.storage.upload_fileobj(file_obj, self.container, doc_path)

        # Generate document ID
        doc_id = self._generate_document_id(
            metadata.get("source_url", ""), metadata.get("title", "")
        )

        # Enrich metadata
        enriched_metadata = {
            **metadata,
            "document_id": doc_id,
            "storage_path": doc_path,
            "storage_provider": self.provider,
            "upload_timestamp": datetime.utcnow().isoformat(),
            "sha256": hashlib.sha256(content_bytes).hexdigest(),
            "size_bytes": len(content_bytes),
        }

        # Save metadata
        self.save_metadata(doc_id, enriched_metadata, meta_path)

        logger.info(f"Saved document: {doc_path}")
        return doc_id

    def load_document(self, document_id: str, metadata: dict[str, Any]) -> bytes:
        """Load document content from storage.

        Args:
            document_id: Document ID
            metadata: Document metadata (with storage_path)

        Returns:
            Document content as bytes

        Raises:
            ValueError: If document not found
        """
        storage_path = metadata.get("storage_path")
        if not storage_path:
            msg = f"No storage_path in metadata for document {document_id}"
            raise ValueError(msg)

        if not self.storage.file_exists(self.container, storage_path):
            msg = f"Document not found: {storage_path}"
            raise ValueError(msg)

        # Download document
        from io import BytesIO

        file_obj = BytesIO()
        self.storage.download_fileobj(self.container, storage_path, file_obj)
        file_obj.seek(0)

        return file_obj.read()

    def save_metadata(
        self,
        document_id: str,
        metadata: dict[str, Any],
        metadata_path: str | None = None,
    ) -> None:
        """Save document metadata to storage.

        Args:
            document_id: Document ID
            metadata: Metadata dictionary
            metadata_path: Optional custom metadata path
        """
        if metadata_path is None:
            metadata_path = f"metadata/{document_id}.json"

        # Convert metadata to JSON
        metadata_json = json.dumps(metadata, indent=2)

        # Upload metadata
        from io import BytesIO

        file_obj = BytesIO(metadata_json.encode("utf-8"))
        self.storage.upload_fileobj(file_obj, self.container, metadata_path)

        logger.debug(f"Saved metadata: {metadata_path}")

    def load_metadata(self, document_id: str) -> dict[str, Any]:
        """Load document metadata from storage.

        Args:
            document_id: Document ID

        Returns:
            Metadata dictionary

        Raises:
            ValueError: If metadata not found
        """
        metadata_path = f"metadata/{document_id}.json"

        if not self.storage.file_exists(self.container, metadata_path):
            msg = f"Metadata not found for document: {document_id}"
            raise ValueError(msg)

        # Download metadata
        from io import BytesIO

        file_obj = BytesIO()
        self.storage.download_fileobj(self.container, metadata_path, file_obj)
        file_obj.seek(0)

        return json.loads(file_obj.read().decode("utf-8"))

    def save_chunks(self, chunks: list[dict[str, Any]], document_id: str) -> None:
        """Save processed chunks to storage.

        Args:
            chunks: List of chunk dictionaries
            document_id: Parent document ID
        """
        for i, chunk in enumerate(chunks):
            chunk_path = f"chunks/{document_id}/{i:06d}.json"
            chunk_data = json.dumps(chunk, indent=2)

            # Upload chunk
            from io import BytesIO

            file_obj = BytesIO(chunk_data.encode("utf-8"))
            self.storage.upload_fileobj(file_obj, self.container, chunk_path)

        logger.info(f"Saved {len(chunks)} chunks for document {document_id}")

    def load_chunks(self, document_id: str) -> list[dict[str, Any]]:
        """Load all chunks for a document from storage.

        Args:
            document_id: Document ID

        Returns:
            List of chunk dictionaries
        """
        chunk_prefix = f"chunks/{document_id}/"
        chunk_files = self.storage.list_files(self.container, chunk_prefix)

        chunks = []
        for chunk_file in sorted(chunk_files):
            from io import BytesIO

            file_obj = BytesIO()
            self.storage.download_fileobj(self.container, chunk_file, file_obj)
            file_obj.seek(0)

            chunk_data = json.loads(file_obj.read().decode("utf-8"))
            chunks.append(chunk_data)

        logger.info(f"Loaded {len(chunks)} chunks for document {document_id}")
        return chunks

    def list_documents(
        self,
        jurisdiction: str | None = None,
        category: str | None = None,
        topic: str | None = None,
    ) -> list[dict[str, Any]]:
        """List documents in storage with optional filters.

        Args:
            jurisdiction: Filter by jurisdiction
            category: Filter by category
            topic: Filter by topic

        Returns:
            List of document metadata dictionaries
        """
        # Build prefix based on filters (metadata alongside documents)
        prefix_parts = ["documents"]
        if jurisdiction:
            prefix_parts.append(jurisdiction.replace(" ", "_").lower())
            if category:
                prefix_parts.append(category.replace(" ", "_").lower())
                if topic:
                    prefix_parts.append(topic.replace(" ", "_").lower())

        prefix = "/".join(prefix_parts) + "/"

        # List metadata files (*.metadata.json)
        metadata_files = self.storage.list_files(self.container, prefix)

        documents = []
        for meta_file in metadata_files:
            if not meta_file.endswith(".metadata.json"):
                continue

            try:
                from io import BytesIO

                file_obj = BytesIO()
                self.storage.download_fileobj(self.container, meta_file, file_obj)
                file_obj.seek(0)

                metadata = json.loads(file_obj.read().decode("utf-8"))
                documents.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to load metadata from {meta_file}: {e}")
                continue

        logger.info(f"Listed {len(documents)} documents with prefix: {prefix}")
        return documents

    def delete_document(self, document_id: str, metadata: dict[str, Any]) -> None:
        """Delete document and associated data from storage.

        Args:
            document_id: Document ID
            metadata: Document metadata (with storage paths)
        """
        # Delete document
        if storage_path := metadata.get("storage_path"):
            if self.storage.file_exists(self.container, storage_path):
                self.storage.delete_file(self.container, storage_path)
                logger.info(f"Deleted document: {storage_path}")

            # Delete metadata (stored alongside document)
            metadata_path = f"{storage_path}.metadata.json"
            if self.storage.file_exists(self.container, metadata_path):
                self.storage.delete_file(self.container, metadata_path)
                logger.info(f"Deleted metadata: {metadata_path}")

        # Delete chunks
        chunk_prefix = f"chunks/{document_id}/"
        chunk_files = self.storage.list_files(self.container, chunk_prefix)
        for chunk_file in chunk_files:
            self.storage.delete_file(self.container, chunk_file)

        logger.info(f"Deleted {len(chunk_files)} chunks for document {document_id}")

    def get_storage_info(self) -> dict[str, Any]:
        """Get information about the storage backend.

        Returns:
            Dictionary with storage backend information
        """
        return {
            "provider": self.provider,
            "container": self.container,
            "backend_type": type(self.storage.backend).__name__,
        }
