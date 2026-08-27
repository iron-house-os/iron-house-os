"""Scope completed-work cost idempotency keys to their project.

Revision ID: 20260827_0034
Revises: 20260827_0033
"""

import sqlalchemy as sa
from alembic import op


revision = "20260827_0034"
down_revision = "20260827_0033"
branch_labels = None
depends_on = None


OLD_CONSTRAINT = "uq_financial_entries_source_allocation"
NEW_CONSTRAINT = "uq_financial_entries_project_source_key"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("financial_entries"):
        return
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("financial_entries")
    }
    if OLD_CONSTRAINT in unique_constraints or NEW_CONSTRAINT not in unique_constraints:
        with op.batch_alter_table("financial_entries") as batch_op:
            if OLD_CONSTRAINT in unique_constraints:
                batch_op.drop_constraint(OLD_CONSTRAINT, type_="unique")
            if NEW_CONSTRAINT not in unique_constraints:
                batch_op.create_unique_constraint(
                    NEW_CONSTRAINT,
                    ["project_id", "source_type", "source_key"],
                )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("financial_entries"):
        return
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("financial_entries")
    }
    if NEW_CONSTRAINT in unique_constraints or OLD_CONSTRAINT not in unique_constraints:
        with op.batch_alter_table("financial_entries") as batch_op:
            if NEW_CONSTRAINT in unique_constraints:
                batch_op.drop_constraint(NEW_CONSTRAINT, type_="unique")
            if OLD_CONSTRAINT not in unique_constraints:
                batch_op.create_unique_constraint(
                    OLD_CONSTRAINT,
                    ["source_type", "source_id", "source_key"],
                )
