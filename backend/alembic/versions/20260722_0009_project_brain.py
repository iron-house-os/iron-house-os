"""Build 229 durable Project Brain.

Revision ID: 20260722_0009
Revises: 20260722_0008
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0009"
down_revision = "20260722_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "project_memories" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "project_memories",
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("authority", sa.Integer(), server_default="60", nullable=False),
        sa.Column("source_date", sa.DateTime(timezone=True)),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("imported_by", sa.String(255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_memories_source_kind", "project_memories", ["source_kind"])
    op.create_index("ix_project_memories_source_id", "project_memories", ["source_id"], unique=True)
    op.create_index("ix_project_memories_authority", "project_memories", ["authority"])


def downgrade() -> None:
    op.drop_table("project_memories")
