"""Bootstrap service: seeds DocumentSource/DocumentFile DB records from YAML config.

Run automatically on app startup (idempotent). After the first run, the DB is the
source of truth — YAML is only consulted when new entries are added there and haven't
yet been bootstrapped.

Flow:
  1. Load documents_config.yml via load_documents_config()
  2. For each config entry, create a source plugin via DocumentSourceFactory
  3. If no matching DocumentSource row exists → INSERT (lifecycle_state defaults to 'detect')
  4. For each download_url → INSERT DocumentFile row if not already present
  5. Existing rows are never overwritten (DB wins)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session

from green_gov_rag.etl.loader import load_documents_config
from green_gov_rag.etl.sources.factory import DocumentSourceFactory
from green_gov_rag.models.document import DocumentFile, DocumentSource

logger = logging.getLogger(__name__)


@dataclass
class BootstrapResult:
    """Summary of a bootstrap run."""

    sources_created: int = 0
    files_created: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def bootstrap_db_from_yaml(
    session: Session,
    config_path: str = "configs/documents_config.yml",
) -> BootstrapResult:
    """Seed DocumentSource and DocumentFile rows from YAML config.

    Safe to call on every startup — skips rows that already exist.

    Args:
        session: Active SQLModel session.
        config_path: Path to documents_config.yml.

    Returns:
        BootstrapResult summary.
    """
    result = BootstrapResult()

    if not Path(config_path).exists():
        logger.warning("Bootstrap skipped: config not found at %s", config_path)
        return result

    doc_configs = load_documents_config(config_path)
    factory = DocumentSourceFactory()
    now = datetime.now(timezone.utc)

    for doc_config in doc_configs:
        try:
            source_plugin = factory.create_source(doc_config)
            urls: list[str] = doc_config.get("download_urls", [])
            if not urls:
                continue

            # Use the first URL to generate a stable source ID
            source_id = source_plugin.get_document_id(urls[0])

            # --- DocumentSource ---
            existing_source = session.get(DocumentSource, source_id)
            if existing_source is None:
                new_source = DocumentSource(
                    id=source_id,
                    title=doc_config.get("title", ""),
                    source_url=doc_config.get("source_url", ""),
                    jurisdiction=doc_config.get("jurisdiction", ""),
                    topic=doc_config.get("topic", ""),
                    region=doc_config.get("region"),
                    category=doc_config.get("category"),
                    esg_metadata=doc_config.get("esg_metadata"),
                    spatial_metadata=doc_config.get("spatial_metadata"),
                    status="pending",
                    db_bootstrapped_at=now,
                )
                session.add(new_source)
                result.sources_created += 1
                logger.debug(
                    "Bootstrap: created source %s (%s)",
                    source_id,
                    doc_config.get("title"),
                )
            else:
                result.skipped += 1

            # --- DocumentFile rows (one per download URL) ---
            for url in urls:
                file_id = source_plugin.get_document_id(url)
                existing_file = session.get(DocumentFile, file_id)
                if existing_file is None:
                    filename = url.rsplit("/", 1)[-1] or url
                    new_file = DocumentFile(
                        id=file_id,
                        source_id=source_id,
                        filename=filename,
                        file_url=url,
                        content_hash="",  # populated after first download
                        lifecycle_state="detect",
                        discovered_at=now,
                    )
                    session.add(new_file)
                    result.files_created += 1

        except Exception as exc:
            msg = f"Bootstrap error for '{doc_config.get('title', '?')}': {exc}"
            logger.warning(msg)
            result.errors.append(msg)

    session.commit()
    logger.info(
        "Bootstrap complete: %d sources created, %d files created, %d skipped, %d errors",
        result.sources_created,
        result.files_created,
        result.skipped,
        len(result.errors),
    )
    return result
