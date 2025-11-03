"""Database writer for ETL pipeline.

Supports tracking both local filesystem and cloud storage paths
for documents and chunks with normalized schema:
- document_sources: Config entries (1:many with files)
- document_files: Individual PDFs
- document_chunks: Text segments
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlmodel import Session, select

from green_gov_rag.models import Chunk, DocumentFile, DocumentSource
from green_gov_rag.models.base import engine
from green_gov_rag.models.document_version import DocumentVersion

logger = logging.getLogger(__name__)


def create_document_id(source_url: str, title: str) -> str:
    """Generate unique document ID from URL and title."""
    content = f"{source_url}::{title}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def save_document_source(
    title: str,
    source_url: str,
    jurisdiction: str,
    topic: str,
    region: Optional[str] = None,
    category: Optional[str] = None,
    metadata: Optional[dict] = None,
    esg_metadata: Optional[dict] = None,
    spatial_metadata: Optional[dict] = None,
    status: str = "pending",
) -> DocumentSource:
    """Save document source (config entry) to database.

    Args:
        title: Source title
        source_url: Source website URL (homepage)
        jurisdiction: Federal/State/Local
        topic: Document topic
        region: Geographic region
        category: Document category
        metadata: Additional metadata
        esg_metadata: ESG/emissions metadata (frameworks, scopes, gases, etc.)
        spatial_metadata: Spatial metadata (LGA codes, state, spatial scope, etc.)
        status: Processing status

    Returns:
        DocumentSource: Saved document source
    """
    source_id = create_document_id(source_url, title)

    with Session(engine) as session:
        # Check if source already exists
        statement = select(DocumentSource).where(DocumentSource.id == source_id)
        existing_source = session.exec(statement).first()

        if existing_source:
            # Update existing source
            existing_source.title = title
            existing_source.source_url = source_url
            existing_source.jurisdiction = jurisdiction
            existing_source.topic = topic
            existing_source.region = region
            existing_source.category = category
            existing_source.metadata_ = metadata
            existing_source.esg_metadata = esg_metadata
            existing_source.spatial_metadata = spatial_metadata
            existing_source.status = status
            existing_source.updated_at = datetime.now(timezone.utc)

            session.add(existing_source)
            session.commit()
            session.refresh(existing_source)

            logger.info(f"Updated document source {source_id}")
            return existing_source
        else:
            # Create new source
            source = DocumentSource(
                id=source_id,
                title=title,
                source_url=source_url,
                jurisdiction=jurisdiction,
                topic=topic,
                region=region,
                category=category,
                metadata_=metadata,
                esg_metadata=esg_metadata,
                spatial_metadata=spatial_metadata,
                status=status,
            )

            session.add(source)
            session.commit()
            session.refresh(source)

            logger.info(f"Created document source {source_id}")
            return source


def save_document_file(
    source_id: str,
    filename: str,
    file_url: str,
    content_hash: str,
    file_size_bytes: Optional[int] = None,
    file_metadata: Optional[dict] = None,
    status: str = "pending",
) -> DocumentFile:
    """Save document file (individual PDF) to database.

    Args:
        source_id: Parent document source ID
        filename: Original filename
        file_url: Direct download URL for this file
        content_hash: SHA256 hash of file content
        file_size_bytes: File size in bytes
        file_metadata: File-specific metadata (page count, format, etc.)
        status: Processing status

    Returns:
        DocumentFile: Saved document file
    """
    # Generate file_id from source_id and filename
    file_id = f"{source_id}_{hashlib.md5(filename.encode()).hexdigest()[:8]}"

    with Session(engine) as session:
        # Check if file already exists
        statement = select(DocumentFile).where(DocumentFile.id == file_id)
        existing_file = session.exec(statement).first()

        if existing_file:
            # Update existing file
            existing_file.filename = filename
            existing_file.file_url = file_url
            existing_file.content_hash = content_hash
            existing_file.file_size_bytes = file_size_bytes
            existing_file.file_metadata = file_metadata
            existing_file.status = status

            session.add(existing_file)
            session.commit()
            session.refresh(existing_file)

            logger.info(f"Updated document file {file_id}")
            return existing_file
        else:
            # Create new file
            doc_file = DocumentFile(
                id=file_id,
                source_id=source_id,
                filename=filename,
                file_url=file_url,
                content_hash=content_hash,
                file_size_bytes=file_size_bytes,
                file_metadata=file_metadata,
                status=status,
            )

            session.add(doc_file)
            session.commit()
            session.refresh(doc_file)

            logger.info(f"Created document file {file_id}")
            return doc_file


def update_document_source_status(
    source_id: str,
    status: str,
    error_message: Optional[str] = None,
    chunk_count: Optional[int] = None,
    embedding_model: Optional[str] = None,
) -> None:
    """Update document source processing status.

    Args:
        source_id: Document source ID
        status: New status (pending/processing/completed/failed)
        error_message: Error message if failed
        chunk_count: Number of chunks created
        embedding_model: Embedding model used
    """
    with Session(engine) as session:
        statement = select(DocumentSource).where(DocumentSource.id == source_id)
        source = session.exec(statement).first()

        if source:
            source.status = status
            source.updated_at = datetime.now(timezone.utc)

            if error_message:
                source.error_message = error_message

            if chunk_count is not None:
                source.chunk_count = chunk_count

            if embedding_model:
                source.embedding_model = embedding_model

            if status == "completed":
                source.processed_at = datetime.now(timezone.utc)

            session.add(source)
            session.commit()


def update_document_file_status(
    file_id: str,
    status: str,
    error_message: Optional[str] = None,
    chunk_count: Optional[int] = None,
) -> None:
    """Update document file processing status.

    Args:
        file_id: Document file ID
        status: New status (pending/downloading/processing/completed/failed)
        error_message: Error message if failed
        chunk_count: Number of chunks from this file
    """
    with Session(engine) as session:
        statement = select(DocumentFile).where(DocumentFile.id == file_id)
        doc_file = session.exec(statement).first()

        if doc_file:
            doc_file.status = status

            if error_message:
                doc_file.error_message = error_message

            if chunk_count is not None:
                doc_file.chunk_count = chunk_count

            if status == "completed":
                doc_file.processed_at = datetime.now(timezone.utc)
            elif status == "downloading":
                doc_file.downloaded_at = datetime.now(timezone.utc)

            session.add(doc_file)
            session.commit()


def save_chunk(
    source_id: str,
    file_id: str,
    chunk_index: int,
    text: str,
    page_number: Optional[int] = None,
    page_range: Optional[list[int]] = None,
    section_title: Optional[str] = None,
    section_hierarchy: Optional[list[str]] = None,
    clause_reference: Optional[str] = None,
    source_pdf_url: Optional[str] = None,
    deep_link: Optional[str] = None,
    citation: Optional[str] = None,
    embedding_index: Optional[int] = None,
    embedding_model: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Chunk:
    """Save text chunk to database.

    Args:
        source_id: Parent document source ID (config entry)
        file_id: Specific file this chunk came from
        chunk_index: Chunk position in document
        text: Chunk text
        page_number: Page number if PDF
        page_range: Page range if chunk spans multiple pages [start, end]
        section_title: Section title
        section_hierarchy: Full section hierarchy from document root
        clause_reference: Legal clause/section reference (e.g., 's.3.2.1')
        source_pdf_url: Direct PDF URL for deep linking
        deep_link: Deep link to specific section/page in source document
        citation: Formatted citation string for display
        embedding_index: Index in vector store
        embedding_model: Embedding model used
        metadata: Additional chunk metadata

    Returns:
        Chunk: Saved chunk
    """
    with Session(engine) as session:
        # Check if chunk already exists (by file_id + chunk_index)
        statement = select(Chunk).where(
            Chunk.file_id == file_id, Chunk.chunk_index == chunk_index
        )
        existing_chunk = session.exec(statement).first()

        if existing_chunk:
            # Update existing chunk
            existing_chunk.source_id = source_id
            existing_chunk.text = text
            existing_chunk.char_count = len(text)
            existing_chunk.page_number = page_number
            existing_chunk.page_range = page_range
            existing_chunk.section_title = section_title
            existing_chunk.section_hierarchy = section_hierarchy
            existing_chunk.clause_reference = clause_reference
            existing_chunk.source_pdf_url = source_pdf_url
            existing_chunk.deep_link = deep_link
            existing_chunk.citation = citation
            existing_chunk.embedding_index = embedding_index
            existing_chunk.embedding_model = embedding_model
            existing_chunk.metadata_ = metadata

            session.add(existing_chunk)
            session.commit()
            session.refresh(existing_chunk)

            logger.debug(
                f"Updated chunk {file_id}[{chunk_index}] "
                f"(page: {page_number}, section: {section_title})"
            )
            return existing_chunk
        else:
            # Create new chunk
            chunk = Chunk(
                source_id=source_id,
                file_id=file_id,
                chunk_index=chunk_index,
                text=text,
                char_count=len(text),
                page_number=page_number,
                page_range=page_range,
                section_title=section_title,
                section_hierarchy=section_hierarchy,
                clause_reference=clause_reference,
                source_pdf_url=source_pdf_url,
                deep_link=deep_link,
                citation=citation,
                embedding_index=embedding_index,
                embedding_model=embedding_model,
                metadata_=metadata,
            )

            session.add(chunk)
            session.commit()
            session.refresh(chunk)

            logger.debug(
                f"Created chunk {file_id}[{chunk_index}] "
                f"(page: {page_number}, section: {section_title})"
            )
            return chunk


def get_document_source_by_id(source_id: str) -> Optional[DocumentSource]:
    """Get document source by ID."""
    with Session(engine) as session:
        statement = select(DocumentSource).where(DocumentSource.id == source_id)
        return session.exec(statement).first()


def get_document_file_by_id(file_id: str) -> Optional[DocumentFile]:
    """Get document file by ID."""
    with Session(engine) as session:
        statement = select(DocumentFile).where(DocumentFile.id == file_id)
        return session.exec(statement).first()


def get_chunks_by_source(source_id: str) -> list[Chunk]:
    """Get all chunks for a document source."""
    with Session(engine) as session:
        statement = select(Chunk).where(Chunk.source_id == source_id)
        return list(session.exec(statement).all())


def get_chunks_by_file(file_id: str) -> list[Chunk]:
    """Get all chunks for a document file."""
    with Session(engine) as session:
        statement = select(Chunk).where(Chunk.file_id == file_id)
        return list(session.exec(statement).all())


def save_document_source_from_storage_metadata(
    storage_metadata: dict[str, Any],
) -> DocumentSource:
    """Save document source to database from cloud storage metadata.

    Args:
        storage_metadata: Metadata dict from ETL storage adapter

    Returns:
        DocumentSource: Saved document source
    """
    return save_document_source(
        title=storage_metadata.get("title", "Untitled"),
        source_url=storage_metadata.get("source_url", ""),
        jurisdiction=storage_metadata.get("jurisdiction", "unknown"),
        topic=storage_metadata.get("topic", "general"),
        region=storage_metadata.get("region"),
        category=storage_metadata.get("category"),
        metadata=storage_metadata,
        esg_metadata=storage_metadata.get("esg_metadata"),
        spatial_metadata=storage_metadata.get("spatial_metadata"),
        status="pending",
    )


def save_chunks_from_storage(
    source_id: str,
    file_id: str,
    chunks: list[dict[str, Any]],
    embedding_model: Optional[str] = None,
) -> list[Chunk]:
    """Save chunks to database from cloud storage chunk data.

    Args:
        source_id: Parent document source ID
        file_id: Parent document file ID
        chunks: List of chunk dicts from ETL storage adapter
        embedding_model: Optional embedding model name

    Returns:
        List of saved Chunk objects
    """
    saved_chunks = []

    for i, chunk_data in enumerate(chunks):
        metadata = chunk_data.get("metadata", {})
        chunk = save_chunk(
            source_id=source_id,
            file_id=file_id,
            chunk_index=metadata.get("chunk_id", i),
            text=chunk_data.get("content", ""),
            page_number=metadata.get("page_number"),
            page_range=metadata.get("page_range"),
            section_title=metadata.get("section_title"),
            section_hierarchy=metadata.get("section_hierarchy"),
            clause_reference=metadata.get("clause_reference"),
            source_pdf_url=metadata.get("source_pdf_url"),
            deep_link=metadata.get("deep_link"),
            citation=metadata.get("citation"),
            embedding_model=embedding_model,
            metadata=metadata,
        )
        saved_chunks.append(chunk)

    logger.info(f"Saved {len(saved_chunks)} chunks for file {file_id}")
    return saved_chunks


def save_document_version(
    source_id: str,
    content_hash: str,
    source_url: str,
    file_size_bytes: Optional[int] = None,
    change_type: str = "new",
    remote_last_modified: Optional[datetime] = None,
    remote_etag: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> DocumentVersion:
    """Create a new document version record.

    Args:
        source_id: Parent document source ID
        content_hash: SHA256 hash of document content
        source_url: URL where document was retrieved
        file_size_bytes: File size in bytes
        change_type: Type of change ('new', 'updated', 'unchanged')
        remote_last_modified: Last-Modified header from server
        remote_etag: ETag header from server
        metadata: Additional version metadata

    Returns:
        DocumentVersion: Created version record
    """
    with Session(engine) as session:
        # Get current version number for this source
        statement = (
            select(DocumentVersion)
            .where(DocumentVersion.source_id == source_id)
            .order_by(DocumentVersion.version_number.desc())  # type: ignore[attr-defined]
        )
        latest_version = session.exec(statement).first()

        version_number = (latest_version.version_number + 1) if latest_version else 1

        # Mark previous version as superseded if this is an update
        if latest_version and latest_version.is_current:
            latest_version.is_current = False
            latest_version.superseded_at = datetime.now(timezone.utc)
            session.add(latest_version)

        # Create new version
        version = DocumentVersion(
            source_id=source_id,
            version_number=version_number,
            content_hash=content_hash,
            source_url=source_url,
            file_size_bytes=file_size_bytes,
            change_type=change_type,
            remote_last_modified=remote_last_modified,
            remote_etag=remote_etag,
            metadata_=metadata,
            downloaded_at=datetime.now(timezone.utc),
            status="completed",
            is_current=True,
        )

        session.add(version)
        session.commit()
        session.refresh(version)

        logger.info(
            f"Created version {version_number} for source {source_id} "
            f"(type: {change_type})"
        )

        return version
