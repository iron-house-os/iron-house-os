"""Build 240 Google Calendar connection.

Revision ID: 20260726_0011
Revises: 20260725_0010
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONType

revision = "20260726_0011"
down_revision = "20260725_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "google_calendar_connections" not in tables:
        op.create_table(
            "google_calendar_connections",
            sa.Column("owner_account_id", sa.Uuid(), nullable=False),
            sa.Column("encrypted_access_token", sa.Text()),
            sa.Column("encrypted_refresh_token", sa.Text()),
            sa.Column("token_expires_at", sa.DateTime(timezone=True)),
            sa.Column("scopes_json", JSONType, nullable=False),
            sa.Column("status", sa.String(32), server_default="connected", nullable=False),
            sa.Column("last_synced_at", sa.DateTime(timezone=True)),
            sa.Column("last_error", sa.String(500)),
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
            sa.ForeignKeyConstraint(["owner_account_id"], ["user_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_account_id"),
        )
        op.create_index(
            "ix_google_calendar_connections_owner_account_id",
            "google_calendar_connections",
            ["owner_account_id"],
            unique=True,
        )
    if "google_calendar_oauth_states" not in tables:
        op.create_table(
            "google_calendar_oauth_states",
            sa.Column("state_digest", sa.String(64), nullable=False),
            sa.Column("owner_account_id", sa.Uuid(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True)),
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
            sa.ForeignKeyConstraint(["owner_account_id"], ["user_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_google_calendar_oauth_states_state_digest",
            "google_calendar_oauth_states",
            ["state_digest"],
            unique=True,
        )
        op.create_index(
            "ix_google_calendar_oauth_states_owner_account_id",
            "google_calendar_oauth_states",
            ["owner_account_id"],
        )
        op.create_index(
            "ix_google_calendar_oauth_states_expires_at",
            "google_calendar_oauth_states",
            ["expires_at"],
        )


def downgrade() -> None:
    op.drop_table("google_calendar_oauth_states")
    op.drop_table("google_calendar_connections")
