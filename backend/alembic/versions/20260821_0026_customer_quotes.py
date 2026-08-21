"""add customer quote register and award handoff

Revision ID: 20260821_0026
Revises: 20260821_0025
"""

import sqlalchemy as sa
from alembic import op


revision = "20260821_0026"
down_revision = "20260821_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("customer_quotes"):
        return
    op.create_table(
        "customer_quotes",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("quote_number", sa.String(length=80), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=True),
        sa.Column("customer_phone", sa.String(length=80), nullable=True),
        sa.Column("site_address", sa.String(length=500), nullable=True),
        sa.Column("scope_summary", sa.Text(), nullable=False),
        sa.Column("line_items_json", sa.JSON(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("exclusions_json", sa.JSON(), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("gst", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("quote_date", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("record_revision", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=320), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.String(length=320), nullable=True),
        sa.Column("acceptance_reference", sa.String(length=500), nullable=True),
        sa.Column("acceptance_note", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_number"),
    )
    for column in ("project_id", "status"):
        op.create_index(op.f(f"ix_customer_quotes_{column}"), "customer_quotes", [column], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("customer_quotes"):
        return
    indexes = {index["name"] for index in inspector.get_indexes("customer_quotes")}
    for column in ("status", "project_id"):
        index_name = op.f(f"ix_customer_quotes_{column}")
        if index_name in indexes:
            op.drop_index(index_name, table_name="customer_quotes")
    op.drop_table("customer_quotes")
