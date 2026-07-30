"""Add the project-scoped supplier quote register.

Revision ID: 20260729_0012
Revises: 20260726_0011
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONType

revision = "20260729_0012"
down_revision = "20260726_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("quotes")
    }
    current_columns = {
        "project_id",
        "rfq_package_id",
        "supplier_name",
        "quote_reference",
        "revision",
        "line_item_code",
        "line_item_description",
        "scope",
        "scope_type",
        "is_qualified",
        "qualification_notes",
        "is_selected",
        "selection_reason",
        "exclusions",
    }
    if current_columns.issubset(existing_columns):
        return

    with op.batch_alter_table("quotes") as batch:
        batch.add_column(sa.Column("project_id", sa.Uuid()))
        batch.add_column(sa.Column("rfq_package_id", sa.Uuid()))
        batch.add_column(sa.Column("supplier_name", sa.String(255)))
        batch.add_column(sa.Column("quote_reference", sa.String(120)))
        batch.add_column(sa.Column("revision", sa.Integer(), server_default="1", nullable=False))
        batch.add_column(sa.Column("line_item_code", sa.String(120)))
        batch.add_column(sa.Column("line_item_description", sa.String(500)))
        batch.add_column(sa.Column("scope", sa.Text()))
        batch.add_column(sa.Column("scope_type", sa.String(80), server_default="material", nullable=False))
        batch.add_column(sa.Column("is_qualified", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch.add_column(sa.Column("qualification_notes", JSONType, server_default="[]", nullable=False))
        batch.add_column(sa.Column("is_selected", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column("selection_reason", sa.Text()))
        batch.add_column(sa.Column("exclusions", JSONType, server_default="[]", nullable=False))

    op.execute(
        """
        UPDATE quotes
        SET project_id = (SELECT rfqs.project_id FROM rfqs WHERE rfqs.id = quotes.rfq_id),
            supplier_name = (
                SELECT suppliers.name FROM suppliers WHERE suppliers.id = quotes.supplier_id
            ),
            scope = COALESCE(notes, 'Legacy supplier quote')
        """
    )

    with op.batch_alter_table("quotes") as batch:
        batch.alter_column("project_id", nullable=False)
        batch.alter_column("supplier_name", nullable=False)
        batch.alter_column("scope", nullable=False)
        batch.alter_column("rfq_id", nullable=True)
        batch.alter_column("supplier_id", nullable=True)
        batch.create_foreign_key("fk_quotes_project_id", "projects", ["project_id"], ["id"])
        batch.create_foreign_key(
            "fk_quotes_rfq_package_id",
            "rfq_packages",
            ["rfq_package_id"],
            ["id"],
        )
        batch.create_index("ix_quotes_project_id", ["project_id"])
        batch.create_index("ix_quotes_rfq_package_id", ["rfq_package_id"])


def downgrade() -> None:
    with op.batch_alter_table("quotes") as batch:
        batch.drop_index("ix_quotes_rfq_package_id")
        batch.drop_index("ix_quotes_project_id")
        batch.drop_constraint("fk_quotes_rfq_package_id", type_="foreignkey")
        batch.drop_constraint("fk_quotes_project_id", type_="foreignkey")
        batch.alter_column("supplier_id", nullable=False)
        batch.alter_column("rfq_id", nullable=False)
        for column in (
            "exclusions",
            "selection_reason",
            "is_selected",
            "qualification_notes",
            "is_qualified",
            "scope_type",
            "scope",
            "line_item_description",
            "line_item_code",
            "revision",
            "quote_reference",
            "supplier_name",
            "rfq_package_id",
            "project_id",
        ):
            batch.drop_column(column)
