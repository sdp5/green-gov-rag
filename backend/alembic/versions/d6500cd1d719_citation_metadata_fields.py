"""citation metadata fields

Revision ID: d6500cd1d719
Revises: 44a0cb447101
Create Date: 2025-11-03 16:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'd6500cd1d719'
down_revision = '44a0cb447101'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new citation and metadata fields to documents and chunks tables."""

    # Add new fields to documents table
    op.add_column('documents', sa.Column('esg_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('documents', sa.Column('spatial_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # Add new fields to chunks table
    op.add_column('chunks', sa.Column('page_range', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('chunks', sa.Column('section_hierarchy', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('chunks', sa.Column('clause_reference', sa.String(), nullable=True))
    op.add_column('chunks', sa.Column('deep_link', sa.String(), nullable=True))
    op.add_column('chunks', sa.Column('citation', sa.String(), nullable=True))

    # Add composite index for efficient chunk lookups by document_id + chunk_index
    op.create_index(
        'ix_chunks_document_id_chunk_index',
        'chunks',
        ['document_id', 'chunk_index'],
        unique=False
    )

    # Add session_id to query_history table for user-specific query tracking
    op.add_column('query_history', sa.Column('session_id', sa.String(), nullable=True))
    op.create_index('ix_query_history_session_id', 'query_history', ['session_id'], unique=False)

    # Add traffic analytics fields to query_history
    op.add_column('query_history', sa.Column('ip_address', sa.String(), nullable=True))
    op.add_column('query_history', sa.Column('user_agent', sa.String(), nullable=True))
    op.add_column('query_history', sa.Column('referer', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove citation and metadata fields from documents and chunks tables."""

    # Remove query_history traffic analytics fields
    op.drop_column('query_history', 'referer')
    op.drop_column('query_history', 'user_agent')
    op.drop_column('query_history', 'ip_address')

    # Remove query_history session tracking
    op.drop_index('ix_query_history_session_id', table_name='query_history')
    op.drop_column('query_history', 'session_id')

    # Remove chunks index
    op.drop_index('ix_chunks_document_id_chunk_index', table_name='chunks')

    # Remove fields from chunks table
    op.drop_column('chunks', 'citation')
    op.drop_column('chunks', 'deep_link')
    op.drop_column('chunks', 'clause_reference')
    op.drop_column('chunks', 'section_hierarchy')
    op.drop_column('chunks', 'page_range')

    # Remove fields from documents table
    op.drop_column('documents', 'spatial_metadata')
    op.drop_column('documents', 'esg_metadata')