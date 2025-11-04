"""Populate document_versions table from existing document_files.

This script creates initial DocumentVersion records for all document files
in the database that don't have version tracking yet.

With the normalized schema:
- document_sources: Config entries (sources)
- document_files: Individual PDFs
- document_versions: Track changes to individual files over time

This script creates version records for each document file.

Usage:
    python -m green_gov_rag.scripts.populate_document_versions
"""

import logging

from sqlmodel import Session, select

from green_gov_rag.etl.db_writer import engine, save_document_version
from green_gov_rag.models import DocumentFile, DocumentVersion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_document_versions() -> None:
    """Create initial DocumentVersion records for each document file."""
    with Session(engine) as session:
        # Get all document files
        files = session.exec(select(DocumentFile)).all()
        logger.info(f"Found {len(files)} document files")

        created_count = 0
        skipped_count = 0

        for doc_file in files:
            logger.info(f"Processing file: {doc_file.filename} (ID: {doc_file.id})")

            # Check if version already exists for this file
            existing = session.exec(
                select(DocumentVersion).where(DocumentVersion.file_id == doc_file.id)
            ).first()

            if existing:
                logger.info(f"  ⊘ Version already exists for file {doc_file.id}")
                skipped_count += 1
                continue

            # Create version record for this file
            try:
                save_document_version(
                    file_id=doc_file.id,
                    source_id=doc_file.source_id,
                    content_hash=doc_file.content_hash,
                    source_url=doc_file.file_url,
                    file_size_bytes=doc_file.file_size_bytes,
                    change_type="new",
                    metadata={
                        "note": "Initial version from normalized schema",
                        "filename": doc_file.filename,
                    },
                )
                created_count += 1
                logger.info(
                    f"  ✓ Created version for {doc_file.filename} "
                    f"(hash: {doc_file.content_hash[:8]}..., "
                    f"size: {doc_file.file_size_bytes or 0} bytes)"
                )

            except Exception as e:
                logger.error(f"  ✗ Failed to process {doc_file.id}: {e}")
                skipped_count += 1

    logger.info(
        f"\n{'='*60}\n"
        f"Summary:\n"
        f"  Files processed: {len(files)}\n"
        f"  Versions created: {created_count}\n"
        f"  Skipped/Failed: {skipped_count}\n"
        f"{'='*60}"
    )


if __name__ == "__main__":
    populate_document_versions()
