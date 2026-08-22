"""add recoverable project trash

Revision ID: 20260822_0029
Revises: 20260822_0028
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_0029"
down_revision = "20260822_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("projects")}
    if "deleted_at" not in columns:
        op.add_column(
            "projects", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
    indexes = {index["name"] for index in inspector.get_indexes("projects")}
    index_name = op.f("ix_projects_deleted_at")
    if index_name not in indexes:
        op.create_index(index_name, "projects", ["deleted_at"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("projects")}
    index_name = op.f("ix_projects_deleted_at")
    if index_name in indexes:
        op.drop_index(index_name, table_name="projects")
    columns = {column["name"] for column in inspector.get_columns("projects")}
    if "deleted_at" in columns:
        op.drop_column("projects", "deleted_at")
