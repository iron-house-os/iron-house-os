"""add management-assigned equipment safety procedure references

Revision ID: 20260818_0020
Revises: 20260816_0019
"""

import sqlalchemy as sa
from alembic import op


revision = "20260818_0020"
down_revision = "20260816_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("equipment"):
        return
    columns = {column["name"] for column in inspector.get_columns("equipment")}
    if "safety_procedure_codes" not in columns:
        op.add_column(
            "equipment",
            sa.Column("safety_procedure_codes", sa.JSON(), nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("equipment"):
        return
    columns = {column["name"] for column in inspector.get_columns("equipment")}
    if "safety_procedure_codes" in columns:
        op.drop_column("equipment", "safety_procedure_codes")
