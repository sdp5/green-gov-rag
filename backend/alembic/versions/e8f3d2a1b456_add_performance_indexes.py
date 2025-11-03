"""add performance indexes

Revision ID: e8f3d2a1b456
Revises: d6500cd1d719
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e8f3d2a1b456'
down_revision = 'd6500cd1d719'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for common query patterns."""

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

    # Index 4: Documents by url_hash (ETL duplicate detection)
    op.create_index(
        'idx_documents_url_hash',
        'documents',
        ['url_hash'],
        unique=False
    )

    # Index 5: Documents by status (common in admin queries)
    op.create_index(
        'idx_documents_status',
        'documents',
        ['status'],
        unique=False
    )

    # Index 6: Chunks by page_number (citation lookups)
    op.create_index(
        'idx_chunks_page_number',
        'chunks',
        ['page_number'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""

    op.drop_index('idx_chunks_page_number', table_name='chunks')
    op.drop_index('idx_documents_status', table_name='documents')
    op.drop_index('idx_documents_url_hash', table_name='documents')
    op.drop_index('idx_query_history_created_at', table_name='query_history')
    op.drop_index('idx_documents_jurisdiction', table_name='documents')
    op.drop_index('idx_chunks_document_id_chunk_index', table_name='chunks')
