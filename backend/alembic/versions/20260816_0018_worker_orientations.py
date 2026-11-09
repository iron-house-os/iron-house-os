"""Add durable worker orientation evidence and deployment controls.

Revision ID: 20260816_0018
Revises: 20260806_0017
"""

from alembic import op
import sqlalchemy as sa


revision = "20260816_0018"
down_revision = "20260806_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("worker_orientations"):
        return
    op.create_table(
        "worker_orientations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("onboarding_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid()),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("site_name", sa.String(255)),
        sa.Column("trigger", sa.String(40), nullable=False),
        sa.Column("orientation_date", sa.Date(), nullable=False),
        sa.Column("instructor_name", sa.String(200), nullable=False),
        sa.Column("instructor_email", sa.String(255)),
        sa.Column("supervisor_name", sa.String(200), nullable=False),
        sa.Column("supervisor_email", sa.String(255)),
        sa.Column("document_version", sa.String(80), nullable=False),
        sa.Column("topics", sa.JSON(), nullable=False),
        sa.Column("competency_result", sa.String(30), nullable=False),
        sa.Column("ppe_verified", sa.Boolean(), nullable=False),
        sa.Column("qualifications_verified", sa.Boolean(), nullable=False),
        sa.Column("worker_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("worker_acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("supporting_document_ids", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["onboarding_id"], ["employee_onboardings.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_orientations_onboarding_id", "worker_orientations", ["onboarding_id"])
    op.create_index("ix_worker_orientations_project_id", "worker_orientations", ["project_id"])


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("worker_orientations"):
        return
    op.drop_index("ix_worker_orientations_project_id", table_name="worker_orientations")
    op.drop_index("ix_worker_orientations_onboarding_id", table_name="worker_orientations")
    op.drop_table("worker_orientations")
