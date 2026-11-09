"""add explicit employee assignment to equipment

Revision ID: 20260820_0022
Revises: 20260820_0021
"""

import sqlalchemy as sa
from alembic import op


revision = "20260820_0022"
down_revision = "20260820_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("equipment"):
        return
    columns = {column["name"] for column in inspector.get_columns("equipment")}
    if "assigned_employee_id" in columns:
        return
    with op.batch_alter_table("equipment") as batch:
        batch.add_column(sa.Column("assigned_employee_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_equipment_assigned_employee_id_employees",
            "employees",
            ["assigned_employee_id"],
            ["id"],
        )
        batch.create_index("ix_equipment_assigned_employee_id", ["assigned_employee_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("equipment"):
        return
    columns = {column["name"] for column in inspector.get_columns("equipment")}
    if "assigned_employee_id" not in columns:
        return
    with op.batch_alter_table("equipment") as batch:
        batch.drop_index("ix_equipment_assigned_employee_id")
        batch.drop_constraint("fk_equipment_assigned_employee_id_employees", type_="foreignkey")
        batch.drop_column("assigned_employee_id")
