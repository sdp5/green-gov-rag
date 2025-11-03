"""add performance indexes

Revision ID: e8f3d2a1b456
Revises: d6500cd1d719
Create Date: 2025-01-15 10:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'e8f3d2a1b456'
down_revision = 'd6500cd1d719'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for common query patterns and source_pdf_url field."""

    # Add source_pdf_url column to documents table
    op.add_column('documents', sa.Column('source_pdf_url', sa.String(), nullable=True))

    # Add source_pdf_url column to chunks table
    op.add_column('chunks', sa.Column('source_pdf_url', sa.String(), nullable=True))

    # Index 0: Chunks by source_pdf_url (for deep link lookups)
    op.create_index(
        'idx_chunks_source_pdf_url',
        'chunks',
        ['source_pdf_url'],
        unique=False
    )

    # Index 1: Chunks by document_id + chunk_index (common in /documents/{id}/chunks)
    op.create_index(
        'idx_chunks_document_id_chunk_index',
        'chunks',
        ['document_id', 'chunk_index'],
        unique=False
    )

    # Index 2: Documents by jurisdiction (common in /documents?jurisdiction=SA)
    op.create_index(
        'idx_documents_jurisdiction',
        'documents',
        ['jurisdiction'],
        unique=False
    )

    # Index 3: Query history by created_at (analytics queries)
    op.create_index(
        'idx_query_history_created_at',
        'query_history',
        ['created_at'],
        unique=False,
        postgresql_using='btree',
        postgresql_ops={'created_at': 'DESC'}
    )

    # Index 4: Documents by status (common in admin queries)
    op.create_index(
        'idx_documents_status',
        'documents',
        ['status'],
        unique=False
    )

    # Index 5: Chunks by page_number (citation lookups)
    op.create_index(
        'idx_chunks_page_number',
        'chunks',
        ['page_number'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes and source_pdf_url field."""

    op.drop_index('idx_chunks_page_number', table_name='chunks')
    op.drop_index('idx_chunks_source_pdf_url', table_name='chunks')
    op.drop_index('idx_documents_status', table_name='documents')
    op.drop_index('idx_query_history_created_at', table_name='query_history')
    op.drop_index('idx_documents_jurisdiction', table_name='documents')
    op.drop_index('idx_chunks_document_id_chunk_index', table_name='chunks')

    # Remove source_pdf_url columns
    op.drop_column('chunks', 'source_pdf_url')
    op.drop_column('documents', 'source_pdf_url')
