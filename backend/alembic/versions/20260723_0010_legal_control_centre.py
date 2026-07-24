"""Build 230 AI Legal Control Centre.

Revision ID: 20260723_0010
Revises: 20260722_0009
"""
from alembic import op
import sqlalchemy as sa


revision = "20260723_0010"
down_revision = "20260722_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "legal_matters" not in tables:
        op.create_table(
            "legal_matters",
            sa.Column("owner_account_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("matter_type", sa.String(60), nullable=False),
            sa.Column("project_name", sa.String(200)),
            sa.Column("counterparty", sa.String(200)),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="open"),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="unassessed"),
            sa.Column("confidentiality", sa.String(40), nullable=False, server_default="standard"),
            sa.Column("jurisdiction", sa.String(80), nullable=False, server_default="British Columbia, Canada"),
            sa.Column("assigned_specialists", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("created_by", sa.String(255), nullable=False),
            sa.Column("reviewed_by", sa.String(255)),
            sa.Column("reviewed_at", sa.DateTime(timezone=True)),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["owner_account_id"], ["user_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("owner_account_id", "matter_type", "status", "risk_level"):
            op.create_index(f"ix_legal_matters_{column}", "legal_matters", [column])
    if "legal_analyses" not in tables:
        op.create_table(
            "legal_analyses",
            sa.Column("matter_id", sa.Uuid(), nullable=False),
            sa.Column("requested_by", sa.String(255), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
            sa.Column("specialist_keys", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("executive_summary", sa.Text(), nullable=False),
            sa.Column("draft_text", sa.Text()),
            sa.Column("issues", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("recommendations", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("questions_for_counsel", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("source_ids", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("disclaimer", sa.Text(), nullable=False),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["matter_id"], ["legal_matters.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_legal_analyses_matter_id", "legal_analyses", ["matter_id"])
    if "legal_deadlines" not in tables:
        op.create_table(
            "legal_deadlines",
            sa.Column("matter_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("source_basis", sa.Text(), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="candidate"),
            sa.Column("created_by", sa.String(255), nullable=False),
            sa.Column("verified_by", sa.String(255)),
            sa.Column("verified_at", sa.DateTime(timezone=True)),
            sa.Column("evidence_reference", sa.String(1000)),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["matter_id"], ["legal_matters.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("matter_id", "due_date", "status"):
            op.create_index(f"ix_legal_deadlines_{column}", "legal_deadlines", [column])
    if "legal_audit_events" not in tables:
        op.create_table(
            "legal_audit_events",
            sa.Column("matter_id", sa.Uuid()),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("actor", sa.String(255), nullable=False),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("outcome", sa.String(40), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["matter_id"], ["legal_matters.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_legal_audit_events_matter_id", "legal_audit_events", ["matter_id"])
        op.create_index("ix_legal_audit_events_action", "legal_audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("legal_audit_events")
    op.drop_table("legal_deadlines")
    op.drop_table("legal_analyses")
    op.drop_table("legal_matters")
