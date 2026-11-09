"""Build 226 financial control ledger.

Revision ID: 20260722_0006
Revises: 20260722_0005
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260722_0006"
down_revision = "20260722_0005"
branch_labels = None
depends_on = None


def _json_type():
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    if "financial_entries" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "financial_entries",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("cost_code", sa.String(32), nullable=False),
        sa.Column("entry_type", sa.String(40), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("vendor_name", sa.String(255)),
        sa.Column("reference", sa.String(120)),
        sa.Column("description", sa.Text()),
        sa.Column("source_type", sa.String(40), server_default="manual", nullable=False),
        sa.Column("source_id", sa.Uuid()),
        sa.Column("status", sa.String(40), server_default="posted", nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("project_id", "cost_code", "entry_type", "category", "entry_date", "reference", "status"):
        op.create_index(f"ix_financial_entries_{column}", "financial_entries", [column])


def downgrade() -> None:
    op.drop_table("financial_entries")
