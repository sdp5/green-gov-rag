#!/usr/bin/env python3
"""Document ingestion script for GreenGovRAG.

Supports both local filesystem and cloud storage (AWS S3, Azure Blob)
via the ETL storage adapter. Provider selection is controlled via
CLOUD_PROVIDER environment variable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml

from green_gov_rag.config import settings
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter
from green_gov_rag.types import (
    DEFAULT_DOWNLOAD_BACKOFF,
    DEFAULT_DOWNLOAD_RETRIES,
    DEFAULT_DOWNLOAD_TIMEOUT,
    DEFAULT_DOWNLOADED_FILENAME,
    DEFAULT_HASH_CHUNK_SIZE,
    DEFAULT_HTTP_HEADERS,
    DOWNLOAD_ERRORS_LOG_FILENAME,
    FAILED_DOWNLOADS_FILENAME,
    METADATA_FILE_SUFFIX,
)

# Paths (for backward compatibility with local mode)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "configs" / "documents_config.yml"
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging setup
logging.basicConfig(
    filename=LOG_DIR / DOWNLOAD_ERRORS_LOG_FILENAME,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def load_config():
    """Load YAML configuration for documents."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sha256sum(file_path):
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(DEFAULT_HASH_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(
    url,
    dest_path,
    retries=DEFAULT_DOWNLOAD_RETRIES,
    backoff=DEFAULT_DOWNLOAD_BACKOFF,
) -> bool:
    """Download file with retry logic.

    Uses browser-like headers to avoid bot detection (Cloudflare, etc.).

    Args:
        url: URL to download
        dest_path: Destination file path
        retries: Number of retry attempts
        backoff: Backoff multiplier for retries

    Returns:
        True if successful, False otherwise
    """
    attempt = 0
    last_status_code = None

    while attempt < retries:
        try:
            resp = requests.get(
                url,
                timeout=DEFAULT_DOWNLOAD_TIMEOUT,
                headers=DEFAULT_HTTP_HEADERS,
                allow_redirects=True,
            )
            last_status_code = resp.status_code

            # Check for bot protection (403/503 from Cloudflare, etc.)
            if resp.status_code in (403, 503):
                # Check if it's Cloudflare protection
                is_cloudflare = (
                    "cloudflare" in resp.headers.get("Server", "").lower()
                    or "cf-ray" in resp.headers
                    or "cf-mitigated" in resp.headers
                )
                if is_cloudflare:
                    logger.warning(
                        f"Cloudflare protection detected for {url}. "
                        "Manual download required."
                    )
                    # Don't retry Cloudflare-protected URLs
                    return False

            resp.raise_for_status()

            with open(dest_path, "wb") as f:
                f.write(resp.content)
            return True

        except requests.exceptions.HTTPError as e:
            attempt += 1
            if last_status_code in (403, 403):
                logger.error(
                    f"Access denied (HTTP {last_status_code}) for {url}. "
                    "Likely bot protection. Skipping retries."
                )
                break
            logger.error(f"HTTP error downloading {url}: {e} (attempt {attempt})")
            if attempt < retries:
                time.sleep(backoff**attempt)

        except Exception as e:
            attempt += 1
            logger.error(f"Error downloading {url}: {e} (attempt {attempt})")
            if attempt < retries:
                time.sleep(backoff**attempt)

    return False


def safe_filename(url):
    """Generate a safe filename from a URL."""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    return filename or DEFAULT_DOWNLOADED_FILENAME


def process_document(
    doc: dict[str, Any],
    storage_adapter: ETLStorageAdapter | None = None,
    use_cloud: bool = False,
) -> None:
    """Download and save a single document with metadata.

    Args:
        doc: Document configuration dictionary
        storage_adapter: Optional ETL storage adapter (for cloud storage)
        use_cloud: Whether to use cloud storage (requires storage_adapter)
    """
    title = doc.get("title", "untitled")
    jurisdiction = doc.get("jurisdiction", "unknown")
    category = doc.get("category", "misc")
    topic = doc.get("topic", "general")
    urls = doc.get("download_urls", [])

    # Extract ESG metadata if present (NGER/ISSB compliance)
    esg_metadata = doc.get("esg_metadata", {})
    spatial_metadata = doc.get("spatial_metadata", {})

    for url in urls:
        # Build metadata
        metadata = {
            "title": title,
            "jurisdiction": jurisdiction,
            "category": category,
            "topic": topic,
            "source_url": url,
        }

        # Add ESG metadata if present
        if esg_metadata:
            metadata["esg_metadata"] = esg_metadata

        # Add spatial metadata if present
        if spatial_metadata:
            metadata["spatial_metadata"] = spatial_metadata

        # Use cloud storage if enabled
        if use_cloud and storage_adapter:
            try:
                doc_id = storage_adapter.download_from_url(url, metadata)
                print(f"✅ Downloaded to cloud: {url} (ID: {doc_id})")
            except Exception as e:
                logger.error(f"Failed to download {url} to cloud: {e}", exc_info=True)
                print(f"❌ Failed to download: {url}")
        else:
            # Use local filesystem (backward compatibility)
            _process_document_local(doc, metadata)


def _process_document_local(doc: dict[str, Any], metadata: dict[str, Any]) -> None:
    """Process document using local filesystem (legacy mode).

    Args:
        doc: Document configuration
        metadata: Document metadata
    """
    jurisdiction = metadata["jurisdiction"].replace(" ", "_")
    category = metadata["category"].replace(" ", "_")
    topic = metadata["topic"].replace(" ", "_")
    url = metadata["source_url"]

    filename = safe_filename(url)
    dest_dir = RAW_DATA_DIR / jurisdiction / category / topic
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    # Skip if exists
    if dest_path.exists():
        logger.info(f"Skipping {url} — already exists")
        return

    if download_file(url, dest_path):
        metadata["filename"] = filename
        metadata["download_timestamp"] = datetime.utcnow().isoformat()
        metadata["sha256"] = sha256sum(dest_path)

        with open(
            dest_dir / f"{filename}{METADATA_FILE_SUFFIX}",
            "w",
            encoding="utf-8",
        ) as mf:
            json.dump(metadata, mf, indent=2)
        print(f"✅ Downloaded: {url}")
    else:
        # Save failed URL to manual review list
        failed_urls_file = LOG_DIR / FAILED_DOWNLOADS_FILENAME
        with open(failed_urls_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().isoformat()} | {url} | {metadata['title']}\n")
        print(f"❌ Failed to download: {url} (saved to {failed_urls_file})")


def download_documents(docs: list[dict], output_dir: str) -> list[str]:
    """Download multiple documents to output directory.

    :param docs: List of document dicts with 'download_urls' key
    :param output_dir: Directory to save downloaded files
    :return: List of downloaded file paths
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    downloaded_files = []
    for doc in docs:
        title = doc.get("title", "untitled")
        urls = doc.get("download_urls", [])

        for url in urls:
            filename = safe_filename(url)
            dest_path = os.path.join(output_dir, filename)

            if download_file(url, dest_path):
                print(f"✅ Downloaded: {title} -> {filename}")
                downloaded_files.append(dest_path)
            else:
                print(f"❌ Failed: {title} from {url}")

    return downloaded_files


def ingest_documents(
    use_cloud: bool | None = None,
    config_path: str | Path | None = None,
) -> list[str]:
    """Ingest documents from config using cloud or local storage.

    Args:
        use_cloud: Whether to use cloud storage. If None, uses CLOUD_PROVIDER setting.
        config_path: Path to config file. Defaults to CONFIG_PATH.

    Returns:
        List of document IDs (cloud mode) or file paths (local mode)
    """
    # Determine storage mode
    if use_cloud is None:
        use_cloud = settings.cloud_provider != "local"

    # Load config
    if config_path is None:
        config_path = CONFIG_PATH

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    documents = config.get("documents", [])
    print(f"Found {len(documents)} documents in config.")
    print(f"Storage mode: {'cloud' if use_cloud else 'local'}")

    # Initialize storage adapter if using cloud
    storage_adapter = ETLStorageAdapter() if use_cloud else None

    # Process documents
    document_ids = []
    for doc in documents:
        if use_cloud:
            # Cloud mode - returns document IDs
            for url in doc.get("download_urls", []):
                try:
                    metadata = {
                        "title": doc.get("title", "untitled"),
                        "jurisdiction": doc.get("jurisdiction", "unknown"),
                        "category": doc.get("category", "misc"),
                        "topic": doc.get("topic", "general"),
                        "source_url": url,
                        "esg_metadata": doc.get("esg_metadata", {}),
                        "spatial_metadata": doc.get("spatial_metadata", {}),
                    }
                    if storage_adapter:
                        doc_id = storage_adapter.download_from_url(url, metadata)
                        document_ids.append(doc_id)
                        print(f"✅ Downloaded to cloud: {url} (ID: {doc_id})")
                except Exception as e:
                    logger.error(f"Failed to download {url}: {e}", exc_info=True)
                    print(f"❌ Failed: {url}")
        else:
            # Local mode - process using existing logic
            process_document(doc, storage_adapter=None, use_cloud=False)

    return document_ids


def main() -> None:
    """Main entry point for CLI usage."""
    config = load_config()
    documents = config.get("documents", [])
    print(f"Found {len(documents)} documents in config.")

    # Detect storage mode from settings
    use_cloud = settings.cloud_provider != "local"
    print(f"Storage mode: {'cloud' if use_cloud else 'local'}")

    storage_adapter = ETLStorageAdapter() if use_cloud else None

    for doc in documents:
        process_document(doc, storage_adapter=storage_adapter, use_cloud=use_cloud)


if __name__ == "__main__":
    main()
