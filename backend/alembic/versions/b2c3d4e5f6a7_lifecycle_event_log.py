"""Create lifecycle_event_log table.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-03

Creates the lifecycle_event_log table which stores an audit trail
of every DocumentFile lifecycle state transition.
"""

import sqlalchemy as sa

from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lifecycle_event_log",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("from_state", sa.String(), nullable=False),
        sa.Column("to_state", sa.String(), nullable=False),
        sa.Column("triggered_by", sa.String(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["file_id"], ["document_files.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["document_sources.id"]),
    )
    op.create_index(
        "ix_lifecycle_event_log_file_id",
        "lifecycle_event_log",
        ["file_id"],
    )
    op.create_index(
        "ix_lifecycle_event_log_source_id",
        "lifecycle_event_log",
        ["source_id"],
    )
    op.create_index(
        "ix_lifecycle_event_log_created_at",
        "lifecycle_event_log",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_lifecycle_event_log_created_at", table_name="lifecycle_event_log")
    op.drop_index("ix_lifecycle_event_log_source_id", table_name="lifecycle_event_log")
    op.drop_index("ix_lifecycle_event_log_file_id", table_name="lifecycle_event_log")
    op.drop_table("lifecycle_event_log")
