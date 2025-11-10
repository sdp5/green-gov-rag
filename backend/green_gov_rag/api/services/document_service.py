"""Document service."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, func, select

from green_gov_rag.api.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
)
from green_gov_rag.models import DocumentSource
from green_gov_rag.models.base import engine


class DocumentService:
    """Service for document operations."""

    def get_documents(
        self,
        jurisdiction: Optional[str] = None,
        topic: Optional[str] = None,
        region: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DocumentListResponse:
        """Get filtered list of documents.

        Args:
            jurisdiction: Filter by jurisdiction
            topic: Filter by topic
            region: Filter by region
            status: Filter by status
            limit: Max results
            offset: Pagination offset

        Returns:
            DocumentListResponse: Paginated document list
        """
        with Session(engine) as session:
            # Build query
            statement = select(DocumentSource)

            # Apply filters
            if jurisdiction:
                statement = statement.where(DocumentSource.jurisdiction == jurisdiction)
            if topic:
                statement = statement.where(DocumentSource.topic == topic)
            if region:
                statement = statement.where(DocumentSource.region == region)
            if status:
                statement = statement.where(DocumentSource.status == status)

            # Get total count
            count_statement = select(func.count()).select_from(statement.subquery())
            total = session.exec(count_statement).one()

            # Apply pagination
            statement = statement.offset(offset).limit(limit)

            # Execute query
            documents = session.exec(statement).all()

            # Convert to response schema
            doc_responses = [
                DocumentResponse(
                    id=doc.id,
                    title=doc.title,
                    source_url=doc.source_url,
                    jurisdiction=doc.jurisdiction,
                    topic=doc.topic,
                    region=doc.region,
                    category=doc.category,
                    status=doc.status,
                    chunk_count=doc.chunk_count,
                    created_at=doc.created_at,
                    processed_at=doc.processed_at,
                )
                for doc in documents
            ]

            return DocumentListResponse(
                documents=doc_responses,
                total=total,
                limit=limit,
                offset=offset,
            )

    def get_document_by_id(self, document_id: str) -> Optional[DocumentResponse]:
        """Get single document by ID.

        Args:
            document_id: Document ID

        Returns:
            DocumentResponse or None
        """
        with Session(engine) as session:
            statement = select(DocumentSource).where(DocumentSource.id == document_id)
            doc = session.exec(statement).first()

            if not doc:
                return None

            return DocumentResponse(
                id=doc.id,
                title=doc.title,
                source_url=doc.source_url,
                jurisdiction=doc.jurisdiction,
                topic=doc.topic,
                region=doc.region,
                category=doc.category,
                status=doc.status,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at,
                processed_at=doc.processed_at,
            )
