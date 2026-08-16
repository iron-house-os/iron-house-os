"""add controlled customer invoices

Revision ID: 20260816_0018
Revises: 20260806_0017
"""

import sqlalchemy as sa
from alembic import op

revision = "20260816_0018"
down_revision = "20260806_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("customer_invoices"):
        return
    op.create_table(
        "customer_invoices",
        sa.Column("invoice_number", sa.String(80), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column("site_address", sa.String(500)),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("customer_address", sa.String(500), nullable=False),
        sa.Column("customer_phone", sa.String(40)),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("terms", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("line_items_json", sa.JSON(), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(7, 4), nullable=False),
        sa.Column("gst", sa.Numeric(14, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("development_seed_key", sa.String(80), unique=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("issued_by", sa.String(255)),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("invoice_number"),
    )
    for column in ("invoice_number", "project_id", "project_name", "customer_name", "invoice_date", "due_date", "status"):
        op.create_index(f"ix_customer_invoices_{column}", "customer_invoices", [column])


def downgrade() -> None:
    op.drop_table("customer_invoices")
