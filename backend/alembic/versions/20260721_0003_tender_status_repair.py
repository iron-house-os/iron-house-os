"""Repair legacy tender statuses and enforce the current workflow values.

Revision ID: 20260721_0003
Revises: 20260714_0002
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0003"
down_revision = "20260714_0002"
branch_labels = None
depends_on = None

VALID_STATUSES = (
    "new",
    "reviewing",
    "bidding",
    "submitted",
    "awarded",
    "lost",
    "no_bid",
)


def upgrade() -> None:
    # The Phase 1 schema used ``watching``. The intake workflow later replaced
    # that value with ``new``, but the Build 209 baseline adopted populated
    # databases without translating existing rows.
    op.execute(
        sa.text(
            """
            UPDATE tenders
            SET status = CASE
                WHEN lower(coalesce(status, '')) IN ('watching', 'watchlist', 'draft', 'open') THEN 'new'
                WHEN lower(coalesce(status, '')) IN ('shortlisted', 'qualified', 'review') THEN 'reviewing'
                WHEN lower(coalesce(status, '')) IN ('bid', 'pricing', 'active') THEN 'bidding'
                WHEN lower(coalesce(status, '')) IN ('won') THEN 'awarded'
                WHEN lower(coalesce(status, '')) IN ('declined', 'no bid', 'closed') THEN 'no_bid'
                ELSE 'new'
            END
            WHERE status IS NULL
               OR lower(status) NOT IN ('new', 'reviewing', 'bidding', 'submitted', 'awarded', 'lost', 'no_bid')
            """
        )
    )
    with op.batch_alter_table("tenders") as batch_op:
        batch_op.create_check_constraint(
            "ck_tenders_status",
            f"status IN ({', '.join(repr(value) for value in VALID_STATUSES)})",
        )


def downgrade() -> None:
    with op.batch_alter_table("tenders") as batch_op:
        batch_op.drop_constraint("ck_tenders_status", type_="check")
