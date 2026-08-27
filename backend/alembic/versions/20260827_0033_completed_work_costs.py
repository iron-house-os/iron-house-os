"""Add idempotent completed-work actual-cost source keys.

Revision ID: 20260827_0033
Revises: 20260827_0032
"""

import sqlalchemy as sa
from alembic import op


revision = "20260827_0033"
down_revision = "20260827_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("financial_entries"):
        return
    existing_columns = {
        column["name"] for column in inspector.get_columns("financial_entries")
    }
    if "source_key" not in existing_columns:
        with op.batch_alter_table("financial_entries") as batch_op:
            batch_op.add_column(sa.Column("source_key", sa.String(length=80), nullable=True))

    inspector = sa.inspect(op.get_bind())
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("financial_entries")
    }
    if "uq_financial_entries_source_allocation" not in unique_constraints:
        with op.batch_alter_table("financial_entries") as batch_op:
            batch_op.create_unique_constraint(
                "uq_financial_entries_source_allocation",
                ["source_type", "source_id", "source_key"],
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("financial_entries"):
        return
    existing_columns = {
        column["name"] for column in inspector.get_columns("financial_entries")
    }
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("financial_entries")
    }
    with op.batch_alter_table("financial_entries") as batch_op:
        if "uq_financial_entries_source_allocation" in unique_constraints:
            batch_op.drop_constraint(
                "uq_financial_entries_source_allocation",
                type_="unique",
            )
        if "source_key" in existing_columns:
            batch_op.drop_column("source_key")
