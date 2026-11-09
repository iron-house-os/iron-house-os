"""Add Help feedback and management Improvement Inbox.

Revision ID: 20260826_0030
Revises: 20260822_0029
"""

import sqlalchemy as sa
from alembic import op


revision = "20260826_0030"
down_revision = "20260822_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "help_improvements" not in tables:
        op.create_table(
            "help_improvements",
            sa.Column("group_key", sa.String(64), nullable=False),
            sa.Column("feedback_type", sa.String(32), nullable=False),
            sa.Column("route", sa.String(300), nullable=False),
            sa.Column("source_ids_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("evidence_count", sa.Integer(), nullable=False),
            sa.Column(
                "last_seen_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("latest_note", sa.Text(), nullable=True),
            sa.Column("latest_project_name", sa.String(160), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column("reviewed_by", sa.String(255), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("group_key"),
        )
        for column in ("group_key", "feedback_type", "route", "status", "last_seen_at"):
            op.create_index(op.f(f"ix_help_improvements_{column}"), "help_improvements", [column])

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "help_feedback" not in tables:
        op.create_table(
            "help_feedback",
            sa.Column("improvement_id", sa.Uuid(), nullable=False),
            sa.Column("audience", sa.String(32), nullable=False),
            sa.Column("project_name", sa.String(160), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(255), nullable=False),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["improvement_id"], ["help_improvements.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("improvement_id", "audience", "created_by"):
            op.create_index(op.f(f"ix_help_feedback_{column}"), "help_feedback", [column])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "help_feedback" in tables:
        op.drop_table("help_feedback")
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "help_improvements" in tables:
        op.drop_table("help_improvements")
