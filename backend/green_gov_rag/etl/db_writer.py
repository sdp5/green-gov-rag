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
    status: str = "pending",
    storage_path: Optional[str] = None,
    storage_provider: Optional[str] = None,
) -> Document:
    """Save document to database with cloud storage tracking.

    Args:
        title: Document title
        source_url: Source URL
        jurisdiction: Federal/State/Local
        topic: Document topic
        region: Geographic region
        category: Document category
        content: Full text content
        metadata: Additional metadata (will be enriched with storage info)
        status: Processing status
        storage_path: Cloud storage path (if using cloud storage)
        storage_provider: Storage provider (local/aws/azure)

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
            existing_doc.jurisdiction = jurisdiction
            existing_doc.topic = topic
            existing_doc.region = region
            existing_doc.category = category
            existing_doc.content = content
            existing_doc.metadata_ = enriched_metadata
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
                jurisdiction=jurisdiction,
                topic=topic,
                region=region,
                category=category,
                content=content,
                metadata_=enriched_metadata,
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
    section_title: Optional[str] = None,
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
        section_title: Section title
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
        chunk = Chunk(
            document_id=document_id,
            chunk_index=chunk_index,
            text=text,
            char_count=len(text),
            page_number=page_number,
            section_title=section_title,
            embedding_index=embedding_index,
            embedding_model=embedding_model,
            metadata_=enriched_metadata,
        )

        session.add(chunk)
        session.commit()
        session.refresh(chunk)
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
        storage_path=storage_metadata.get("storage_path"),
        storage_provider=storage_metadata.get("storage_provider"),
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
            section_title=metadata.get("section_title"),
            embedding_model=embedding_model,
            metadata=metadata,
            storage_path=f"chunks/{document_id}/{i:06d}.json",
        )
        saved_chunks.append(chunk)

    logger.info(f"Saved {len(saved_chunks)} chunks for document {document_id}")
    return saved_chunks
