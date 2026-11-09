"""add controlled customer quote issue evidence

Revision ID: 20260822_0028
Revises: 20260822_0027
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_0028"
down_revision = "20260822_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("customer_quotes"):
        return
    columns = {column["name"] for column in inspector.get_columns("customer_quotes")}
    additions = (
        ("issue_status", sa.String(length=40), False, "'draft'"),
        ("approved_revision", sa.Integer(), True, None),
        ("approved_snapshot_json", sa.JSON(), True, None),
        ("approved_at", sa.DateTime(timezone=True), True, None),
        ("approved_by", sa.String(length=320), True, None),
        ("issued_at", sa.DateTime(timezone=True), True, None),
        ("issued_by", sa.String(length=320), True, None),
        ("issuance_method", sa.String(length=80), True, None),
        ("issuance_reference", sa.String(length=500), True, None),
    )
    for name, column_type, nullable, server_default in additions:
        if name not in columns:
            op.add_column(
                "customer_quotes",
                sa.Column(name, column_type, nullable=nullable, server_default=server_default),
            )
    indexes = {index["name"] for index in inspector.get_indexes("customer_quotes")}
    index_name = op.f("ix_customer_quotes_issue_status")
    if index_name not in indexes:
        op.create_index(index_name, "customer_quotes", ["issue_status"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("customer_quotes"):
        return
    indexes = {index["name"] for index in inspector.get_indexes("customer_quotes")}
    index_name = op.f("ix_customer_quotes_issue_status")
    if index_name in indexes:
        op.drop_index(index_name, table_name="customer_quotes")
    columns = {column["name"] for column in inspector.get_columns("customer_quotes")}
    for name in (
        "issuance_reference", "issuance_method", "issued_by", "issued_at",
        "approved_by", "approved_at", "approved_snapshot_json", "approved_revision", "issue_status",
    ):
        if name in columns:
            op.drop_column("customer_quotes", name)
