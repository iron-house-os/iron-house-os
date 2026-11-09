"""Add traceable project invoice package provenance.

Revision ID: 20260827_0032
Revises: 20260827_0031
"""

import sqlalchemy as sa
from alembic import op

from app.db.types import JSONType


revision = "20260827_0032"
down_revision = "20260827_0031"
branch_labels = None
depends_on = None


PROVENANCE_COLUMNS = (
    sa.Column("source_package_key", sa.String(length=80), nullable=True),
    sa.Column("source_import_key", sa.String(length=255), nullable=True),
    sa.Column("source_record_ids_json", JSONType, nullable=True),
    sa.Column("closeout_snapshot_json", JSONType, nullable=True),
    sa.Column("package_generated_by", sa.String(length=255), nullable=True),
    sa.Column("package_generated_at", sa.DateTime(timezone=True), nullable=True),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("customer_invoices"):
        return
    existing_columns = {
        column["name"] for column in inspector.get_columns("customer_invoices")
    }
    with op.batch_alter_table("customer_invoices") as batch_op:
        for column in PROVENANCE_COLUMNS:
            if column.name not in existing_columns:
                batch_op.add_column(column)

    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("customer_invoices")}
    if "ix_customer_invoices_source_package_key" not in indexes:
        op.create_index(
            "ix_customer_invoices_source_package_key",
            "customer_invoices",
            ["source_package_key"],
            unique=False,
        )
    if "ix_customer_invoices_source_import_key" not in indexes:
        op.create_index(
            "ix_customer_invoices_source_import_key",
            "customer_invoices",
            ["source_import_key"],
            unique=False,
        )
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("customer_invoices")
    }
    if "uq_customer_invoices_source_package_key" not in unique_constraints:
        with op.batch_alter_table("customer_invoices") as batch_op:
            batch_op.create_unique_constraint(
                "uq_customer_invoices_source_package_key",
                ["source_package_key"],
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("customer_invoices"):
        return
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("customer_invoices")
    }
    indexes = {index["name"] for index in inspector.get_indexes("customer_invoices")}
    existing_columns = {
        column["name"] for column in inspector.get_columns("customer_invoices")
    }
    with op.batch_alter_table("customer_invoices") as batch_op:
        if "uq_customer_invoices_source_package_key" in unique_constraints:
            batch_op.drop_constraint(
                "uq_customer_invoices_source_package_key",
                type_="unique",
            )
        if "ix_customer_invoices_source_import_key" in indexes:
            batch_op.drop_index("ix_customer_invoices_source_import_key")
        if "ix_customer_invoices_source_package_key" in indexes:
            batch_op.drop_index("ix_customer_invoices_source_package_key")
        for column in reversed(PROVENANCE_COLUMNS):
            if column.name in existing_columns:
                batch_op.drop_column(column.name)
