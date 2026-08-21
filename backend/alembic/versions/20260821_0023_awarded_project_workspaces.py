"""add awarded project workspace manifests

Revision ID: 20260821_0023
Revises: 20260820_0022
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260821_0023"
down_revision = "20260820_0022"
branch_labels = None
depends_on = None


def _json_type():
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("projects"):
        return
    columns = {column["name"] for column in inspector.get_columns("projects")}
    with op.batch_alter_table("projects") as batch:
        if "workspace_root" not in columns:
            batch.add_column(sa.Column("workspace_root", sa.String(length=500), nullable=True))
        if "workspace_manifest_json" not in columns:
            batch.add_column(sa.Column("workspace_manifest_json", _json_type(), nullable=True))
        if "workspace_provisioned_at" not in columns:
            batch.add_column(sa.Column("workspace_provisioned_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("projects"):
        return
    columns = {column["name"] for column in inspector.get_columns("projects")}
    with op.batch_alter_table("projects") as batch:
        if "workspace_provisioned_at" in columns:
            batch.drop_column("workspace_provisioned_at")
        if "workspace_manifest_json" in columns:
            batch.drop_column("workspace_manifest_json")
        if "workspace_root" in columns:
            batch.drop_column("workspace_root")
