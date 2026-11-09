"""QuickBooks Online sandbox OAuth connection.

Revision ID: 20260924_0036
Revises: 20260827_0035
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONType

revision = "20260924_0036"
down_revision = "20260827_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "quickbooks_connections" not in tables:
        op.create_table(
            "quickbooks_connections",
            sa.Column("environment", sa.String(16), nullable=False),
            sa.Column("connected_by_account_id", sa.Uuid(), nullable=False),
            sa.Column("realm_id", sa.String(64), nullable=False),
            sa.Column("company_name", sa.String(255), nullable=False),
            sa.Column("legal_name", sa.String(255)),
            sa.Column("encrypted_access_token", sa.Text()),
            sa.Column("encrypted_refresh_token", sa.Text()),
            sa.Column("token_expires_at", sa.DateTime(timezone=True)),
            sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True)),
            sa.Column("scopes_json", JSONType, nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("last_verified_at", sa.DateTime(timezone=True)),
            sa.Column("last_error", sa.String(500)),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["connected_by_account_id"], ["user_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("environment"),
            sa.UniqueConstraint("realm_id"),
        )
        op.create_index("ix_quickbooks_connections_environment", "quickbooks_connections", ["environment"], unique=True)
        op.create_index("ix_quickbooks_connections_connected_by_account_id", "quickbooks_connections", ["connected_by_account_id"])
        op.create_index("ix_quickbooks_connections_realm_id", "quickbooks_connections", ["realm_id"], unique=True)
    if "quickbooks_oauth_states" not in tables:
        op.create_table(
            "quickbooks_oauth_states",
            sa.Column("state_digest", sa.String(64), nullable=False),
            sa.Column("owner_account_id", sa.Uuid(), nullable=False),
            sa.Column("environment", sa.String(16), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True)),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["owner_account_id"], ["user_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_quickbooks_oauth_states_state_digest", "quickbooks_oauth_states", ["state_digest"], unique=True)
        op.create_index("ix_quickbooks_oauth_states_owner_account_id", "quickbooks_oauth_states", ["owner_account_id"])
        op.create_index("ix_quickbooks_oauth_states_expires_at", "quickbooks_oauth_states", ["expires_at"])


def downgrade() -> None:
    op.drop_table("quickbooks_oauth_states")
    op.drop_table("quickbooks_connections")
