"""add encrypted QuickBooks sandbox configuration

Revision ID: 20260924_0037
Revises: 20260924_0036
"""

from alembic import op
import sqlalchemy as sa


revision = "20260924_0037"
down_revision = "20260924_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "quickbooks_configurations" in inspector.get_table_names():
        return
    op.create_table(
        "quickbooks_configurations",
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("configured_by_account_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("encrypted_client_secret", sa.Text(), nullable=False),
        sa.Column("encrypted_token_encryption_key", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["configured_by_account_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_quickbooks_configurations_environment",
        "quickbooks_configurations",
        ["environment"],
        unique=True,
    )
    op.create_index(
        "ix_quickbooks_configurations_configured_by_account_id",
        "quickbooks_configurations",
        ["configured_by_account_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quickbooks_configurations_configured_by_account_id",
        table_name="quickbooks_configurations",
    )
    op.drop_index(
        "ix_quickbooks_configurations_environment",
        table_name="quickbooks_configurations",
    )
    op.drop_table("quickbooks_configurations")
