#!/usr/bin/env python3
"""Document ingestion script for GreenGovRAG.
Reads configs/documents_config.yml and downloads files into data/raw/,
storing metadata alongside each file.
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]
import yaml

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "configs" / "documents_config.yml"
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging setup
logging.basicConfig(
    filename=LOG_DIR / "download_errors.log",
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
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url, dest_path, retries=3, backoff=2):
    """Download file with retry logic."""
    attempt = 0
    while attempt < retries:
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            attempt += 1
            logger.error(f"Error downloading {url}: {e} (attempt {attempt})")
            time.sleep(backoff**attempt)
    return False


def safe_filename(url):
    """Generate a safe filename from a URL."""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    return filename or "downloaded_file"


def process_document(doc):
    """Download and save a single document with metadata."""
    title = doc.get("title", "untitled")
    jurisdiction = doc.get("jurisdiction", "unknown").replace(" ", "_")
    category = doc.get("category", "misc").replace(" ", "_")
    topic = doc.get("topic", "general").replace(" ", "_")
    urls = doc.get("download_urls", [])

    for url in urls:
        filename = safe_filename(url)
        dest_dir = RAW_DATA_DIR / jurisdiction / category / topic
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        # Skip if exists and hash matches
        if dest_path.exists():
            logger.info(f"Skipping {url} — already exists")
            continue

        if download_file(url, dest_path):
            metadata = {
                "title": title,
                "source_url": url,
                "download_timestamp": datetime.utcnow().isoformat(),
                "jurisdiction": jurisdiction,
                "category": category,
                "topic": topic,
                "filename": filename,
                "sha256": sha256sum(dest_path),
            }
            with open(dest_dir / f"{filename}.metadata.json", "w", encoding="utf-8") as mf:
                json.dump(metadata, mf, indent=2)
            print(f"✅ Downloaded: {url}")
        else:
            print(f"❌ Failed to download: {url}")


def main():
    config = load_config()
    documents = config.get("documents", [])
    print(f"Found {len(documents)} documents in config.")

    for doc in documents:
        process_document(doc)


if __name__ == "__main__":
    main()
