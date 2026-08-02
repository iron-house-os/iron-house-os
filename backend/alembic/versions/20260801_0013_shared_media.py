"""Add immutable shared media assets, versions, and record links.

Revision ID: 20260801_0013
Revises: 20260729_0012
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONType

revision = "20260801_0013"
down_revision = "20260729_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    media_tables = {"media_assets", "media_versions", "media_record_links"}
    if media_tables.issubset(existing_tables):
        return
    op.create_table(
        "media_assets",
        sa.Column("original_document_id", sa.Uuid(), nullable=False),
        sa.Column("current_version_id", sa.Uuid()),
        sa.Column("project_id", sa.Uuid()),
        sa.Column("caption", sa.Text()),
        sa.Column("captured_date", sa.Date()),
        sa.Column("location", sa.String(255)),
        sa.Column("category", sa.String(80), nullable=False, server_default="job_photo"),
        sa.Column("controlled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_email", sa.String(255), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["original_document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("original_document_id"),
    )
    op.create_index("ix_media_assets_project_id", "media_assets", ["project_id"])
    op.create_table(
        "media_versions",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("parent_version_id", sa.Uuid()),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("editor_id", sa.Uuid(), nullable=False),
        sa.Column("editor_email", sa.String(255), nullable=False),
        sa.Column("operations", JSONType, nullable=False),
        sa.Column("change_summary", sa.Text()),
        sa.Column("amendment_reason", sa.Text()),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["parent_version_id"], ["media_versions.id"]),
        sa.UniqueConstraint("asset_id", "version_number"),
    )
    op.create_index("ix_media_versions_asset_id", "media_versions", ["asset_id"])
    op.create_table(
        "media_record_links",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("record_type", sa.String(80), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"]),
        sa.UniqueConstraint("asset_id", "record_type", "record_id"),
    )
    op.create_index("ix_media_record_links_asset_id", "media_record_links", ["asset_id"])
    op.create_index("ix_media_record_links_record_id", "media_record_links", ["record_id"])
    op.create_index("ix_media_record_links_record_type", "media_record_links", ["record_type"])


def downgrade() -> None:
    op.drop_table("media_record_links")
    op.drop_table("media_versions")
    op.drop_table("media_assets")
