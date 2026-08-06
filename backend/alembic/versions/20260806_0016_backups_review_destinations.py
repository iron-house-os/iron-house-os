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
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("backups_intakes")}
    if "review_destination" not in columns:
        op.add_column("backups_intakes", sa.Column("review_destination", sa.String(80)))
    if "routing_version" not in columns:
        op.add_column(
            "backups_intakes",
            sa.Column("routing_version", sa.Integer(), nullable=False, server_default="0"),
        )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("backups_intakes")}
    if "ix_backups_intakes_review_destination" not in indexes:
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
