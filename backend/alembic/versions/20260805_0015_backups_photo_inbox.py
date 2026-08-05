"""Add the Backups single-photo intake and audit trail.

Revision ID: 20260805_0015
Revises: 20260802_0014
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONType

revision = "20260805_0015"
down_revision = "20260802_0014"
branch_labels = None
depends_on = None


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if {"backup_intakes", "backup_intake_audit_events"}.issubset(existing):
        return

    op.create_table(
        "backup_intakes",
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("media_sha256", sa.String(64), nullable=False),
        sa.Column("uploader_id", sa.Uuid(), nullable=False),
        sa.Column("uploader_email", sa.String(255), nullable=False),
        sa.Column("uploader_role", sa.String(80), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("project_hint", sa.String(255)),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("detected_type", sa.String(40)),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("destination_type", sa.String(80)),
        sa.Column("destination_record_id", sa.Uuid()),
        sa.Column("error", sa.Text()),
        sa.Column("sensitive_quarantine", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("classifier", sa.String(120)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("processing_started_at", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("routed_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
        *_common_columns(),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"]),
        sa.UniqueConstraint("media_asset_id"),
        sa.UniqueConstraint("uploader_id", "media_sha256"),
        sa.UniqueConstraint("destination_type", "destination_record_id"),
    )
    for column in (
        "media_asset_id", "media_sha256", "uploader_id", "uploader_email", "status",
        "detected_type", "destination_type", "destination_record_id",
    ):
        op.create_index(f"ix_backup_intakes_{column}", "backup_intakes", [column])
    op.create_table(
        "backup_intake_audit_events",
        sa.Column("intake_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("actor_email", sa.String(255), nullable=False),
        sa.Column("from_status", sa.String(40)),
        sa.Column("to_status", sa.String(40)),
        sa.Column("detail_json", JSONType, nullable=False),
        *_common_columns(),
        sa.ForeignKeyConstraint(["intake_id"], ["backup_intakes.id"]),
    )
    op.create_index("ix_backup_intake_audit_events_intake_id", "backup_intake_audit_events", ["intake_id"])
    op.create_index("ix_backup_intake_audit_events_action", "backup_intake_audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("backup_intake_audit_events")
    op.drop_table("backup_intakes")
