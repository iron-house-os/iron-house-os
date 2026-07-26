"""Build 239 controlled meeting minutes.

Revision ID: 20260725_0010
Revises: 20260722_0009
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONType

revision = "20260725_0010"
down_revision = "20260722_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "meeting_minutes" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "meeting_minutes",
        sa.Column("owner_account_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("meeting_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attendees_json", JSONType, nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("priority_points_json", JSONType, nullable=False),
        sa.Column("decisions_json", JSONType, nullable=False),
        sa.Column("action_items_json", JSONType, nullable=False),
        sa.Column("transcription_model", sa.String(120)),
        sa.Column("summary_model", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), server_default="approved", nullable=False),
        sa.Column("consent_confirmed", sa.Boolean(), nullable=False),
        sa.Column("review_confirmed", sa.Boolean(), nullable=False),
        sa.Column("audio_retained", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_by_email", sa.String(255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_account_id"], ["user_accounts.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meeting_minutes_owner_account_id", "meeting_minutes", ["owner_account_id"])
    op.create_index("ix_meeting_minutes_project_id", "meeting_minutes", ["project_id"])


def downgrade() -> None:
    op.drop_table("meeting_minutes")
