"""Add management-controlled review destinations for Backups.

Revision ID: 20260806_0017
Revises: 20260806_0016
"""

from alembic import op
import sqlalchemy as sa


revision = "20260806_0017"
down_revision = "20260806_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("backups_intakes")}
    if "review_destination" not in columns:
        op.add_column("backups_intakes", sa.Column("review_destination", sa.String(80)))
        op.create_index(
            "ix_backups_intakes_review_destination",
            "backups_intakes",
            ["review_destination"],
        )
    op.execute(
        sa.text(
            "UPDATE backups_intakes SET review_destination = 'finance_intake' "
            "WHERE processed_at IS NOT NULL AND review_destination IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_backups_intakes_review_destination", table_name="backups_intakes")
    op.drop_column("backups_intakes", "review_destination")
