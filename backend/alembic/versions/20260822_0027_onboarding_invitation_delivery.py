"""track verified onboarding invitation delivery

Revision ID: 20260822_0027
Revises: 20260821_0026
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_0027"
down_revision = "20260821_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("employee_onboardings"):
        return
    columns = {column["name"] for column in inspector.get_columns("employee_onboardings")}
    additions = {
        "encrypted_invitation_token": sa.Column("encrypted_invitation_token", sa.Text(), nullable=True),
        "invitation_delivery_status": sa.Column(
            "invitation_delivery_status",
            sa.String(length=40),
            nullable=False,
            server_default="not_generated",
        ),
        "invitation_delivery_attempted_at": sa.Column(
            "invitation_delivery_attempted_at", sa.DateTime(timezone=True), nullable=True
        ),
        "invitation_delivered_at": sa.Column(
            "invitation_delivered_at", sa.DateTime(timezone=True), nullable=True
        ),
        "invitation_delivery_error_code": sa.Column(
            "invitation_delivery_error_code", sa.String(length=80), nullable=True
        ),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("employee_onboardings", column)

    op.execute(
        sa.text(
            "UPDATE employee_onboardings "
            "SET invitation_delivery_status = 'unverified' WHERE invited_at IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE employee_onboardings SET status = 'invitation_ready' "
            "WHERE status = 'invitation_sent'"
        )
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("employee_onboardings"):
        return
    op.execute(
        sa.text(
            "UPDATE employee_onboardings SET status = 'invitation_sent' "
            "WHERE status = 'invitation_ready'"
        )
    )
    columns = {column["name"] for column in inspector.get_columns("employee_onboardings")}
    for name in (
        "invitation_delivery_error_code",
        "invitation_delivered_at",
        "invitation_delivery_attempted_at",
        "invitation_delivery_status",
        "encrypted_invitation_token",
    ):
        if name in columns:
            op.drop_column("employee_onboardings", name)
