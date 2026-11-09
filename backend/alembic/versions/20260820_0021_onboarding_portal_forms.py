"""add encrypted employee onboarding portal forms

Revision ID: 20260820_0021
Revises: 20260818_0020
"""

import sqlalchemy as sa
from alembic import op


revision = "20260820_0021"
down_revision = "20260818_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("employee_onboardings"):
        return
    columns = {column["name"] for column in inspector.get_columns("employee_onboardings")}
    if "encrypted_portal_data" not in columns:
        op.add_column(
            "employee_onboardings",
            sa.Column("encrypted_portal_data", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("employee_onboardings"):
        return
    columns = {column["name"] for column in inspector.get_columns("employee_onboardings")}
    if "encrypted_portal_data" in columns:
        op.drop_column("employee_onboardings", "encrypted_portal_data")
