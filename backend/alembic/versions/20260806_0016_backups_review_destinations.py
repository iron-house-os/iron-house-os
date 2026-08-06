"""Add management review destinations to Backups intakes.

Revision ID: 20260806_0016
Revises: 20260805_0015
"""

from alembic import op
import sqlalchemy as sa


revision = "20260806_0016"
down_revision = "20260805_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("backups_intakes", sa.Column("review_destination", sa.String(80)))
    op.add_column(
        "backups_intakes",
        sa.Column("routing_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_backups_intakes_review_destination",
        "backups_intakes",
        ["review_destination"],
    )
    op.execute(
        sa.text(
            "UPDATE backups_intakes SET review_destination = 'finance_intake' "
            "WHERE processed_at IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_backups_intakes_review_destination", table_name="backups_intakes")
    op.drop_column("backups_intakes", "routing_version")
    op.drop_column("backups_intakes", "review_destination")
