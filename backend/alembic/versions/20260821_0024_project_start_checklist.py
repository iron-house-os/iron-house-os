"""add awarded project start checklist

Revision ID: 20260821_0024
Revises: 20260821_0023
"""

import sqlalchemy as sa
from alembic import op


revision = "20260821_0024"
down_revision = "20260821_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("projects") or inspector.has_table("project_start_checklist_items"):
        return
    op.create_table(
        "project_start_checklist_items",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("changed_by", sa.String(length=320), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "code", name="uq_project_start_checklist_project_code"),
    )
    op.create_index(
        op.f("ix_project_start_checklist_items_project_id"),
        "project_start_checklist_items",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("project_start_checklist_items"):
        return
    indexes = {index["name"] for index in inspector.get_indexes("project_start_checklist_items")}
    index_name = op.f("ix_project_start_checklist_items_project_id")
    if index_name in indexes:
        op.drop_index(index_name, table_name="project_start_checklist_items")
    op.drop_table("project_start_checklist_items")
