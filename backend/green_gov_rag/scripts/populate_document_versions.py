"""Populate document_versions table from existing documents.

This script creates initial DocumentVersion records for all documents
in the database that don't have version tracking yet.

Usage:
    python -m green_gov_rag.scripts.populate_document_versions
"""

import hashlib
import logging
from pathlib import Path

from sqlmodel import Session, select

from green_gov_rag.config import settings
from green_gov_rag.etl.db_writer import engine, save_document_version
from green_gov_rag.models import DocumentSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex string of SHA256 hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in 64kb chunks
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def populate_document_versions() -> None:
    """Create initial DocumentVersion records for all existing document sources."""
    with Session(engine) as session:
        # Get all document sources
        statement = select(DocumentSource)
        documents = session.exec(statement).all()

        logger.info(f"Found {len(documents)} documents in database")

        raw_dir = Path(
            settings.raw_data_dir if hasattr(settings, "raw_data_dir") else "./data/raw"
        )
        created_count = 0
        skipped_count = 0

        for doc in documents:
            logger.info(f"Processing document: {doc.id} - {doc.title}")

            # Try to find the PDF file in data/raw/
            # Search by document ID or sanitized title
            search_patterns = [
                f"*{doc.id}*.pdf",
                # Also try to match by title (remove special chars)
                f"*{doc.title.replace(' ', '-').replace('/', '-')[:50]}*.pdf",
            ]

            pdf_files = []
            for pattern in search_patterns:
                pdf_files.extend(list(raw_dir.rglob(pattern)))
                if pdf_files:
                    break

            if not pdf_files:
                logger.warning(
                    f"No PDF file found for {doc.id} (title: {doc.title}). "
                    f"Creating version record without content hash."
                )
                # Create version without file hash
                try:
                    save_document_version(
                        source_id=doc.id,
                        content_hash="unknown",  # Placeholder
                        source_url=doc.source_url,
                        file_size_bytes=None,
                        change_type="new",
                        metadata={
                            "note": "Initial version created from database migration",
                            "title": doc.title,
                        },
                    )
                    created_count += 1
                    logger.info(f"✓ Created version record for {doc.id} (no file hash)")
                except Exception as e:
                    logger.error(f"Failed to create version for {doc.id}: {e}")
                    skipped_count += 1
                continue

            # Use first matching PDF file
            pdf_file = pdf_files[0]
            logger.info(f"  Found PDF: {pdf_file}")

            try:
                # Calculate content hash
                content_hash = calculate_file_hash(pdf_file)
                file_size = pdf_file.stat().st_size

                # Create version record
                save_document_version(
                    source_id=doc.id,
                    content_hash=content_hash,
                    source_url=doc.source_url,
                    file_size_bytes=file_size,
                    change_type="new",
                    metadata={
                        "note": "Initial version created from database migration",
                        "file_path": str(pdf_file),
                        "title": doc.title,
                    },
                )
                created_count += 1
                logger.info(
                    f"✓ Created version record for {doc.id} "
                    f"(hash: {content_hash[:8]}..., size: {file_size} bytes)"
                )

            except Exception as e:
                logger.error(f"Failed to process {doc.id}: {e}")
                skipped_count += 1

    logger.info(
        f"\n{'='*60}\n"
        f"Summary:\n"
        f"  Documents processed: {len(documents)}\n"
        f"  Versions created: {created_count}\n"
        f"  Skipped/Failed: {skipped_count}\n"
        f"{'='*60}"
    )


if __name__ == "__main__":
    populate_document_versions()
