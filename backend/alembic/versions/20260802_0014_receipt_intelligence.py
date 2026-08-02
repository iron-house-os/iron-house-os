"""Add controlled receipt intelligence workflow.

Revision ID: 20260802_0014
Revises: 20260801_0013
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONType

revision = "20260802_0014"
down_revision = "20260801_0013"
branch_labels = None
depends_on = None


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "company_cards" not in existing:
        op.create_table(
            "company_cards",
            sa.Column("brand", sa.String(40), nullable=False), sa.Column("last_four", sa.String(4), nullable=False),
            sa.Column("holder_email", sa.String(255), nullable=False), sa.Column("label", sa.String(120)),
            sa.Column("is_authorized", sa.Boolean(), nullable=False, server_default=sa.true()), *_common_columns(),
            sa.UniqueConstraint("brand", "last_four", "holder_email"),
        )
        for column in ("brand", "last_four", "holder_email", "is_authorized"):
            op.create_index(f"ix_company_cards_{column}", "company_cards", [column])
    if "receipts" not in existing:
        op.create_table(
            "receipts",
            sa.Column("status", sa.String(40), nullable=False, server_default="draft_extraction"),
            sa.Column("submitter_id", sa.Uuid(), nullable=False), sa.Column("submitter_email", sa.String(255), nullable=False),
            sa.Column("media_asset_ids", JSONType, nullable=False), sa.Column("image_hash", sa.String(64), nullable=False),
            sa.Column("vendor_id", sa.Uuid()), sa.Column("vendor_name", sa.String(255)), sa.Column("vendor_address", sa.String(500)),
            sa.Column("reference", sa.String(160)), sa.Column("receipt_date", sa.Date()), sa.Column("receipt_time", sa.String(16)),
            sa.Column("currency", sa.String(3), nullable=False, server_default="CAD"), sa.Column("subtotal", sa.Numeric(14, 2)),
            sa.Column("discounts", sa.Numeric(14, 2), nullable=False, server_default="0"), sa.Column("gst", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("pst", sa.Numeric(14, 2), nullable=False, server_default="0"), sa.Column("other_tax", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("tip", sa.Numeric(14, 2), nullable=False, server_default="0"), sa.Column("total", sa.Numeric(14, 2)),
            sa.Column("payment_method", sa.String(40)), sa.Column("card_brand", sa.String(40)), sa.Column("card_last_four", sa.String(4)),
            sa.Column("company_card_id", sa.Uuid()), sa.Column("employee_email", sa.String(255)),
            sa.Column("treatment", sa.String(40), nullable=False, server_default="needs_review"),
            sa.Column("confidence_json", JSONType, nullable=False), sa.Column("source_regions_json", JSONType, nullable=False),
            sa.Column("flags_json", JSONType, nullable=False), sa.Column("duplicate_of_id", sa.Uuid()),
            sa.Column("approved_by", sa.String(255)), sa.Column("approved_at", sa.DateTime(timezone=True)),
            sa.Column("exported_by", sa.String(255)), sa.Column("exported_at", sa.DateTime(timezone=True)),
            sa.Column("voided_by", sa.String(255)), sa.Column("voided_at", sa.DateTime(timezone=True)),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"), *_common_columns(),
            sa.ForeignKeyConstraint(["vendor_id"], ["suppliers.id"]), sa.ForeignKeyConstraint(["company_card_id"], ["company_cards.id"]),
            sa.ForeignKeyConstraint(["duplicate_of_id"], ["receipts.id"]),
        )
        for column in ("status", "submitter_id", "submitter_email", "image_hash", "vendor_id", "vendor_name", "reference", "receipt_date", "company_card_id", "employee_email", "duplicate_of_id"):
            op.create_index(f"ix_receipts_{column}", "receipts", [column])
    if "receipt_line_items" not in existing:
        op.create_table(
            "receipt_line_items", sa.Column("receipt_id", sa.Uuid(), nullable=False), sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False), sa.Column("normalized_description", sa.String(255)),
            sa.Column("quantity", sa.Numeric(12, 3), nullable=False, server_default="1"), sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
            sa.Column("tax", sa.Numeric(14, 2), nullable=False, server_default="0"), sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
            sa.Column("category", sa.String(80), nullable=False, server_default="uncategorized"), sa.Column("project_id", sa.Uuid()),
            sa.Column("equipment_id", sa.Uuid()), sa.Column("cost_code", sa.String(32)), sa.Column("overhead_category", sa.String(80)),
            sa.Column("treatment", sa.String(40), nullable=False, server_default="needs_review"), sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
            sa.Column("source_region_json", JSONType, nullable=False), sa.Column("flags_json", JSONType, nullable=False), *_common_columns(),
            sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"]), sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]), sa.UniqueConstraint("receipt_id", "position"),
        )
        for column in ("receipt_id", "normalized_description", "category", "project_id", "equipment_id", "cost_code", "overhead_category"):
            op.create_index(f"ix_receipt_line_items_{column}", "receipt_line_items", [column])
    if "receipt_aliases" not in existing:
        op.create_table(
            "receipt_aliases", sa.Column("vendor_id", sa.Uuid(), nullable=False), sa.Column("raw_value", sa.String(255), nullable=False),
            sa.Column("normalized_value", sa.String(255), nullable=False), sa.Column("category", sa.String(80), nullable=False),
            sa.Column("cost_code", sa.String(32)), sa.Column("approved_by", sa.String(255), nullable=False), *_common_columns(),
            sa.ForeignKeyConstraint(["vendor_id"], ["suppliers.id"]), sa.UniqueConstraint("vendor_id", "raw_value"),
        )
        op.create_index("ix_receipt_aliases_vendor_id", "receipt_aliases", ["vendor_id"])
        op.create_index("ix_receipt_aliases_raw_value", "receipt_aliases", ["raw_value"])
    if "receipt_audit_events" not in existing:
        op.create_table(
            "receipt_audit_events", sa.Column("receipt_id", sa.Uuid(), nullable=False), sa.Column("action", sa.String(80), nullable=False),
            sa.Column("actor_email", sa.String(255), nullable=False), sa.Column("from_status", sa.String(40)), sa.Column("to_status", sa.String(40)),
            sa.Column("reason", sa.Text()), sa.Column("changes_json", JSONType, nullable=False), *_common_columns(),
            sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"]),
        )
        op.create_index("ix_receipt_audit_events_receipt_id", "receipt_audit_events", ["receipt_id"])
        op.create_index("ix_receipt_audit_events_action", "receipt_audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("receipt_audit_events")
    op.drop_table("receipt_aliases")
    op.drop_table("receipt_line_items")
    op.drop_table("receipts")
    op.drop_table("company_cards")
