"""add durable workflow drafts

Revision ID: 20260821_0025
Revises: 20260821_0024
"""

import sqlalchemy as sa
from alembic import op


revision = "20260821_0025"
down_revision = "20260821_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("workflow_drafts"):
        return
    op.create_table(
        "workflow_drafts",
        sa.Column("owner_account_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("workflow_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("last_saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_account_id"], ["user_accounts.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("owner_account_id", "project_id", "workflow_type", "status"):
        op.create_index(op.f(f"ix_workflow_drafts_{column}"), "workflow_drafts", [column], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("workflow_drafts"):
        return
    indexes = {index["name"] for index in inspector.get_indexes("workflow_drafts")}
    for column in ("status", "workflow_type", "project_id", "owner_account_id"):
        index_name = op.f(f"ix_workflow_drafts_{column}")
        if index_name in indexes:
            op.drop_index(index_name, table_name="workflow_drafts")
    op.drop_table("workflow_drafts")
