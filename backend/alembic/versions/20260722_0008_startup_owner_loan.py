"""Build 228 startup costs and owner loan ledger.

Revision ID: 20260722_0008
Revises: 20260722_0007
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260722_0008"
down_revision = "20260722_0007"
branch_labels = None
depends_on = None


def _json_type():
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    if "startup_expenses" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "startup_expenses",
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("vendor_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("reference", sa.String(160)),
        sa.Column("source_email", sa.String(255)),
        sa.Column("funding_source", sa.String(40), server_default="owner_loan", nullable=False),
        sa.Column("owner_name", sa.String(255)),
        sa.Column("tax_treatment", sa.String(40), server_default="needs_review", nullable=False),
        sa.Column("status", sa.String(40), server_default="review", nullable=False),
        sa.Column("receipt_metadata", _json_type(), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("expense_date", "category", "funding_source", "status", "reference"):
        op.create_index(f"ix_startup_expenses_{column}", "startup_expenses", [column])


def downgrade() -> None:
    op.drop_table("startup_expenses")
