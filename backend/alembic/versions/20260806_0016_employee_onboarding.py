"""Add employee onboarding records and audit trail.

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
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "employee_onboardings" not in existing:
        op.create_table(
            "employee_onboardings",
            sa.Column("legal_first_name", sa.String(100), nullable=False),
            sa.Column("legal_last_name", sa.String(100), nullable=False),
            sa.Column("preferred_name", sa.String(100)),
            sa.Column("personal_email", sa.String(255), nullable=False),
            sa.Column("mobile_phone", sa.String(40)),
            sa.Column("category", sa.String(40), nullable=False),
            sa.Column("position", sa.String(60), nullable=False),
            sa.Column("supervisor_id", sa.Uuid()),
            sa.Column("employment_type", sa.String(50), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("primary_location", sa.String(150)),
            sa.Column("onboarding_package", sa.String(100)),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("completion_percent", sa.Integer(), nullable=False),
            sa.Column("completed_items", sa.JSON(), nullable=False),
            sa.Column("missing_items", sa.JSON(), nullable=False),
            sa.Column("reviewer_id", sa.Uuid()),
            sa.Column("correction_note", sa.Text()),
            sa.Column("invitation_token_hash", sa.String(64)),
            sa.Column("invitation_expires_at", sa.DateTime(timezone=True)),
            sa.Column("invitation_used_at", sa.DateTime(timezone=True)),
            sa.Column("invitation_revoked_at", sa.DateTime(timezone=True)),
            sa.Column("invited_at", sa.DateTime(timezone=True)),
            sa.Column("submitted_at", sa.DateTime(timezone=True)),
            sa.Column("approved_at", sa.DateTime(timezone=True)),
            sa.Column("activated_at", sa.DateTime(timezone=True)),
            sa.Column("employee_id", sa.Uuid()),
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["supervisor_id"], ["employees.id"]),
            sa.ForeignKeyConstraint(["reviewer_id"], ["user_accounts.id"]),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
            sa.UniqueConstraint("employee_id"),
        )
        op.create_index("ix_employee_onboardings_personal_email", "employee_onboardings", ["personal_email"])
        op.create_index(
            "ix_employee_onboardings_invitation_token_hash",
            "employee_onboardings",
            ["invitation_token_hash"],
            unique=True,
        )

    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "employee_onboarding_audits" not in existing:
        op.create_table(
            "employee_onboarding_audits",
            sa.Column("onboarding_id", sa.Uuid(), nullable=False),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("actor", sa.String(255), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.ForeignKeyConstraint(["onboarding_id"], ["employee_onboardings.id"]),
        )
        op.create_index(
            "ix_employee_onboarding_audits_onboarding_id",
            "employee_onboarding_audits",
            ["onboarding_id"],
        )


def downgrade() -> None:
    op.drop_table("employee_onboarding_audits")
    op.drop_table("employee_onboardings")
