"""Add document lifecycle columns to document_files and document_sources.

Revision ID: a1b2c3d4e5f6
Revises: d7ed7ff5e711
Create Date: 2026-04-03

Adds:
  document_files:
    - lifecycle_state          VARCHAR  DEFAULT 'detect'  (indexed)
    - lifecycle_transitioned_at DATETIME nullable
    - superseded_by_url        VARCHAR  nullable
    - http_last_checked_at     DATETIME nullable
    - http_status_code         INTEGER  nullable

  document_sources:
    - db_bootstrapped_at       DATETIME nullable
    - last_monitored_at        DATETIME nullable
"""

import sqlalchemy as sa

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "d7ed7ff5e711"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # document_files — lifecycle columns
    op.add_column(
        "document_files",
        sa.Column(
            "lifecycle_state",
            sa.String(),
            nullable=False,
            server_default="detect",
        ),
    )
    op.create_index(
        "ix_document_files_lifecycle_state",
        "document_files",
        ["lifecycle_state"],
    )
    op.add_column(
        "document_files",
        sa.Column("lifecycle_transitioned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "document_files",
        sa.Column("superseded_by_url", sa.String(), nullable=True),
    )
    op.add_column(
        "document_files",
        sa.Column("http_last_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "document_files",
        sa.Column("http_status_code", sa.Integer(), nullable=True),
    )

    # document_sources — registry tracking columns
    op.add_column(
        "document_sources",
        sa.Column("db_bootstrapped_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "document_sources",
        sa.Column("last_monitored_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_sources", "last_monitored_at")
    op.drop_column("document_sources", "db_bootstrapped_at")
    op.drop_column("document_files", "http_status_code")
    op.drop_column("document_files", "http_last_checked_at")
    op.drop_column("document_files", "superseded_by_url")
    op.drop_column("document_files", "lifecycle_transitioned_at")
    op.drop_index("ix_document_files_lifecycle_state", table_name="document_files")
    op.drop_column("document_files", "lifecycle_state")
