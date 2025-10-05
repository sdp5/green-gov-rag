"""Database writer for ETL pipeline."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from green_gov_rag.models import Chunk, Document
from green_gov_rag.models.base import engine


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
) -> Document:
    """Save document to database.

    Args:
        title: Document title
        source_url: Source URL
        jurisdiction: Federal/State/Local
        topic: Document topic
        region: Geographic region
        category: Document category
        content: Full text content
        metadata: Additional metadata
        status: Processing status

    Returns:
        Document: Saved document
    """
    doc_id = create_document_id(source_url, title)

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
            existing_doc.metadata_ = metadata
            existing_doc.status = status
            existing_doc.updated_at = datetime.utcnow()

            session.add(existing_doc)
            session.commit()
            session.refresh(existing_doc)
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
                metadata_=metadata,
                status=status,
            )

            session.add(doc)
            session.commit()
            session.refresh(doc)
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
) -> Chunk:
    """Save text chunk to database.

    Args:
        document_id: Parent document ID
        chunk_index: Chunk position in document
        text: Chunk text
        page_number: Page number if PDF
        section_title: Section title
        embedding_index: Index in FAISS vector store
        embedding_model: Embedding model used
        metadata: Additional metadata

    Returns:
        Chunk: Saved chunk
    """
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
            metadata_=metadata,
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
