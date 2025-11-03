"""Database writer for ETL pipeline.

Supports tracking both local filesystem and cloud storage paths
for documents and chunks.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session, select

from green_gov_rag.config import settings
from green_gov_rag.models import Chunk, Document
from green_gov_rag.models.base import engine
from green_gov_rag.models.document_version import DocumentVersion

logger = logging.getLogger(__name__)


def create_document_id(source_url: str, title: str) -> str:
    """Generate unique document ID from URL and title."""
    content = f"{source_url}::{title}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def save_document(
    title: str,
    source_url: str,
    jurisdiction: str,
    topic: str,
    region: Optional[str] = None,
    category: Optional[str] = None,
    content: Optional[str] = None,
    metadata: Optional[dict] = None,
    esg_metadata: Optional[dict] = None,
    spatial_metadata: Optional[dict] = None,
    status: str = "pending",
    storage_path: Optional[str] = None,
    storage_provider: Optional[str] = None,
    source_pdf_url: Optional[str] = None,
) -> Document:
    """Save document to database with cloud storage tracking.

    Args:
        title: Document title
        source_url: Source URL (generic portal/landing page)
        jurisdiction: Federal/State/Local
        topic: Document topic
        region: Geographic region
        category: Document category
        content: Full text content
        metadata: Additional metadata (will be enriched with storage info)
        esg_metadata: ESG/emissions metadata (frameworks, scopes, gases, etc.)
        spatial_metadata: Spatial metadata (LGA codes, state, spatial scope, etc.)
        status: Processing status
        storage_path: Cloud storage path (if using cloud storage)
        storage_provider: Storage provider (local/aws/azure)
        source_pdf_url: Direct PDF URL for deep linking (from download_urls)

    Returns:
        Document: Saved document
    """
    doc_id = create_document_id(source_url, title)

    # Enrich metadata with storage information
    enriched_metadata = metadata.copy() if metadata else {}

    # Add storage tracking
    if storage_path:
        enriched_metadata["storage_path"] = storage_path
    if storage_provider:
        enriched_metadata["storage_provider"] = storage_provider
    else:
        enriched_metadata["storage_provider"] = settings.cloud_provider

    # Add storage mode indicator
    enriched_metadata["storage_mode"] = (
        "cloud" if settings.cloud_provider != "local" else "local"
    )

    with Session(engine) as session:
        # Check if document already exists
        statement = select(Document).where(Document.id == doc_id)
        existing_doc = session.exec(statement).first()

        if existing_doc:
            # Update existing document
            existing_doc.title = title
            existing_doc.source_url = source_url
            existing_doc.source_pdf_url = source_pdf_url
            existing_doc.jurisdiction = jurisdiction
            existing_doc.topic = topic
            existing_doc.region = region
            existing_doc.category = category
            existing_doc.content = content
            existing_doc.metadata_ = enriched_metadata
            existing_doc.esg_metadata = esg_metadata
            existing_doc.spatial_metadata = spatial_metadata
            existing_doc.status = status
            existing_doc.updated_at = datetime.utcnow()

            session.add(existing_doc)
            session.commit()
            session.refresh(existing_doc)

            logger.info(
                f"Updated document {doc_id} with storage: "
                f"{enriched_metadata.get('storage_provider')}"
            )
            return existing_doc
        else:
            # Create new document
            doc = Document(
                id=doc_id,
                title=title,
                source_url=source_url,
                source_pdf_url=source_pdf_url,
                jurisdiction=jurisdiction,
                topic=topic,
                region=region,
                category=category,
                content=content,
                metadata_=enriched_metadata,
                esg_metadata=esg_metadata,
                spatial_metadata=spatial_metadata,
                status=status,
            )

            session.add(doc)
            session.commit()
            session.refresh(doc)

            logger.info(
                f"Created document {doc_id} with storage: "
                f"{enriched_metadata.get('storage_provider')}"
            )
            return doc


def update_document_status(
    document_id: str,
    status: str,
    error_message: Optional[str] = None,
    chunk_count: Optional[int] = None,
    embedding_model: Optional[str] = None,
) -> None:
    """Update document processing status.

    Args:
        document_id: Document ID
        status: New status (pending/processing/completed/failed)
        error_message: Error message if failed
        chunk_count: Number of chunks created
        embedding_model: Embedding model used
    """
    with Session(engine) as session:
        statement = select(Document).where(Document.id == document_id)
        doc = session.exec(statement).first()

        if doc:
            doc.status = status
            doc.updated_at = datetime.utcnow()

            if error_message:
                doc.error_message = error_message

            if chunk_count is not None:
                doc.chunk_count = chunk_count

            if embedding_model:
                doc.embedding_model = embedding_model

            if status == "completed":
                doc.processed_at = datetime.utcnow()

            session.add(doc)
            session.commit()


def save_chunk(
    document_id: str,
    chunk_index: int,
    text: str,
    page_number: Optional[int] = None,
    page_range: Optional[list[int]] = None,
    section_title: Optional[str] = None,
    section_hierarchy: Optional[list[str]] = None,
    clause_reference: Optional[str] = None,
    deep_link: Optional[str] = None,
    citation: Optional[str] = None,
    embedding_index: Optional[int] = None,
    embedding_model: Optional[str] = None,
    metadata: Optional[dict] = None,
    storage_path: Optional[str] = None,
) -> Chunk:
    """Save text chunk to database with cloud storage tracking.

    Args:
        document_id: Parent document ID
        chunk_index: Chunk position in document
        text: Chunk text
        page_number: Page number if PDF
        page_range: Page range if chunk spans multiple pages [start, end]
        section_title: Section title
        section_hierarchy: Full section hierarchy from document root
        clause_reference: Legal clause/section reference (e.g., 's.3.2.1')
        deep_link: Deep link to specific section/page in source document
        citation: Formatted citation string for display
        embedding_index: Index in FAISS vector store
        embedding_model: Embedding model used
        metadata: Additional metadata (will be enriched with storage info)
        storage_path: Cloud storage path for chunk (if using cloud storage)

    Returns:
        Chunk: Saved chunk
    """
    # Enrich metadata with storage information
    enriched_metadata = metadata.copy() if metadata else {}

    if storage_path:
        enriched_metadata["storage_path"] = storage_path
        enriched_metadata["storage_provider"] = settings.cloud_provider

    with Session(engine) as session:
        # Check if chunk already exists (by document_id + chunk_index)
        statement = select(Chunk).where(
            Chunk.document_id == document_id, Chunk.chunk_index == chunk_index
        )
        existing_chunk = session.exec(statement).first()

        if existing_chunk:
            # Update existing chunk
            existing_chunk.text = text
            existing_chunk.char_count = len(text)
            existing_chunk.page_number = page_number
            existing_chunk.page_range = page_range
            existing_chunk.section_title = section_title
            existing_chunk.section_hierarchy = section_hierarchy
            existing_chunk.clause_reference = clause_reference
            existing_chunk.deep_link = deep_link
            existing_chunk.citation = citation
            existing_chunk.embedding_index = embedding_index
            existing_chunk.embedding_model = embedding_model
            existing_chunk.metadata_ = enriched_metadata

            session.add(existing_chunk)
            session.commit()
            session.refresh(existing_chunk)

            logger.debug(
                f"Updated chunk {document_id}[{chunk_index}] "
                f"(page: {page_number}, section: {section_title})"
            )
            return existing_chunk
        else:
            # Create new chunk
            chunk = Chunk(
                document_id=document_id,
                chunk_index=chunk_index,
                text=text,
                char_count=len(text),
                page_number=page_number,
                page_range=page_range,
                section_title=section_title,
                section_hierarchy=section_hierarchy,
                clause_reference=clause_reference,
                deep_link=deep_link,
                citation=citation,
                embedding_index=embedding_index,
                embedding_model=embedding_model,
                metadata_=enriched_metadata,
            )

            session.add(chunk)
            session.commit()
            session.refresh(chunk)

            logger.debug(
                f"Created chunk {document_id}[{chunk_index}] "
                f"(page: {page_number}, section: {section_title})"
            )
            return chunk


def get_document_by_id(document_id: str) -> Optional[Document]:
    """Get document by ID."""
    with Session(engine) as session:
        statement = select(Document).where(Document.id == document_id)
        return session.exec(statement).first()


def get_chunks_by_document(document_id: str) -> list[Chunk]:
    """Get all chunks for a document."""
    with Session(engine) as session:
        statement = select(Chunk).where(Chunk.document_id == document_id)
        return list(session.exec(statement).all())


def save_document_from_storage_metadata(storage_metadata: dict[str, Any]) -> Document:
    """Save document to database from cloud storage metadata.

    This is a convenience function that extracts the necessary fields
    from storage metadata and saves them to the database.

    Args:
        storage_metadata: Metadata dict from ETL storage adapter

    Returns:
        Document: Saved document

    Example:
        >>> from green_gov_rag.etl.storage_adapter import ETLStorageAdapter
        >>> adapter = ETLStorageAdapter()
        >>> metadata = adapter.load_metadata(doc_id)
        >>> doc = save_document_from_storage_metadata(metadata)
    """
    return save_document(
        title=storage_metadata.get("title", "Untitled"),
        source_url=storage_metadata.get("source_url", ""),
        jurisdiction=storage_metadata.get("jurisdiction", "unknown"),
        topic=storage_metadata.get("topic", "general"),
        region=storage_metadata.get("region"),
        category=storage_metadata.get("category"),
        metadata=storage_metadata,
        esg_metadata=storage_metadata.get("esg_metadata"),
        spatial_metadata=storage_metadata.get("spatial_metadata"),
        storage_path=storage_metadata.get("storage_path"),
        storage_provider=storage_metadata.get("storage_provider"),
        source_pdf_url=storage_metadata.get("source_pdf_url"),
        status="pending",
    )


def save_chunks_from_storage(
    document_id: str,
    chunks: list[dict[str, Any]],
    embedding_model: Optional[str] = None,
) -> list[Chunk]:
    """Save chunks to database from cloud storage chunk data.

    Args:
        document_id: Parent document ID
        chunks: List of chunk dicts from ETL storage adapter
        embedding_model: Optional embedding model name

    Returns:
        List of saved Chunk objects

    Example:
        >>> from green_gov_rag.etl.storage_adapter import ETLStorageAdapter
        >>> adapter = ETLStorageAdapter()
        >>> chunks = adapter.load_chunks(doc_id)
        >>> saved = save_chunks_from_storage(doc_id, chunks)
    """
    saved_chunks = []

    for i, chunk_data in enumerate(chunks):
        metadata = chunk_data.get("metadata", {})
        chunk = save_chunk(
            document_id=document_id,
            chunk_index=metadata.get("chunk_id", i),
            text=chunk_data.get("content", ""),
            page_number=metadata.get("page_number"),
            page_range=metadata.get("page_range"),
            section_title=metadata.get("section_title"),
            section_hierarchy=metadata.get("section_hierarchy"),
            clause_reference=metadata.get("clause_reference"),
            deep_link=metadata.get("deep_link"),
            citation=metadata.get("citation"),
            embedding_model=embedding_model,
            metadata=metadata,
            storage_path=f"chunks/{document_id}/{i:06d}.json",
        )
        saved_chunks.append(chunk)

    logger.info(f"Saved {len(saved_chunks)} chunks for document {document_id}")
    return saved_chunks


def save_document_version(
    document_id: str,
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
        document_id: Parent document ID
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
        # Get current version number for this document
        statement = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())  # type: ignore[attr-defined]
        )
        latest_version = session.exec(statement).first()

        version_number = (latest_version.version_number + 1) if latest_version else 1

        # Mark previous version as superseded if this is an update
        if latest_version and latest_version.is_current:
            latest_version.is_current = False
            latest_version.superseded_at = datetime.utcnow()
            session.add(latest_version)

        # Create new version
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            content_hash=content_hash,
            source_url=source_url,
            file_size_bytes=file_size_bytes,
            change_type=change_type,
            remote_last_modified=remote_last_modified,
            remote_etag=remote_etag,
            metadata_=metadata,
            downloaded_at=datetime.utcnow(),
            status="completed",
            is_current=True,
        )

        session.add(version)
        session.commit()
        session.refresh(version)

        logger.info(
            f"Created version {version_number} for document {document_id} "
            f"(type: {change_type})"
        )

        return version
