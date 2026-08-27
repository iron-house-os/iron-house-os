"""add estimate provenance and idempotency to customer quotes

Revision ID: 20260827_0035
Revises: 20260827_0034
"""

import sqlalchemy as sa
from alembic import op


revision = "20260827_0035"
down_revision = "20260827_0034"
branch_labels = None
depends_on = None


WORKSPACE_UNIQUE = "uq_customer_quotes_source_estimate_workspace"
HASH_UNIQUE = "uq_customer_quotes_project_estimate_hash"
WORKSPACE_FK = "fk_customer_quotes_source_estimate_workspace_id_bids"
WORKSPACE_INDEX = "ix_customer_quotes_source_estimate_workspace_id"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("customer_quotes"):
        return
    columns = {column["name"] for column in inspector.get_columns("customer_quotes")}
    with op.batch_alter_table("customer_quotes") as batch_op:
        if "source_estimate_workspace_id" not in columns:
            batch_op.add_column(sa.Column("source_estimate_workspace_id", sa.Uuid(), nullable=True))
        if "source_estimate_hash" not in columns:
            batch_op.add_column(sa.Column("source_estimate_hash", sa.String(length=64), nullable=True))
        if "source_estimate_snapshot_json" not in columns:
            batch_op.add_column(sa.Column("source_estimate_snapshot_json", sa.JSON(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    foreign_keys = {constraint["name"] for constraint in inspector.get_foreign_keys("customer_quotes")}
    unique_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("customer_quotes")
    }
    indexes = {index["name"] for index in inspector.get_indexes("customer_quotes")}
    with op.batch_alter_table("customer_quotes") as batch_op:
        if WORKSPACE_FK not in foreign_keys:
            batch_op.create_foreign_key(
                WORKSPACE_FK,
                "bids",
                ["source_estimate_workspace_id"],
                ["id"],
            )
        if WORKSPACE_UNIQUE not in unique_constraints:
            batch_op.create_unique_constraint(WORKSPACE_UNIQUE, ["source_estimate_workspace_id"])
        if HASH_UNIQUE not in unique_constraints:
            batch_op.create_unique_constraint(HASH_UNIQUE, ["project_id", "source_estimate_hash"])
        if WORKSPACE_INDEX not in indexes:
            batch_op.create_index(WORKSPACE_INDEX, ["source_estimate_workspace_id"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("customer_quotes"):
        return
    columns = {column["name"] for column in inspector.get_columns("customer_quotes")}
    if "source_estimate_workspace_id" not in columns:
        return
    foreign_keys = {constraint["name"] for constraint in inspector.get_foreign_keys("customer_quotes")}
    unique_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("customer_quotes")
    }
    indexes = {index["name"] for index in inspector.get_indexes("customer_quotes")}
    with op.batch_alter_table("customer_quotes") as batch_op:
        if WORKSPACE_INDEX in indexes:
            batch_op.drop_index(WORKSPACE_INDEX)
        if HASH_UNIQUE in unique_constraints:
            batch_op.drop_constraint(HASH_UNIQUE, type_="unique")
        if WORKSPACE_UNIQUE in unique_constraints:
            batch_op.drop_constraint(WORKSPACE_UNIQUE, type_="unique")
        if WORKSPACE_FK in foreign_keys:
            batch_op.drop_constraint(WORKSPACE_FK, type_="foreignkey")
        batch_op.drop_column("source_estimate_snapshot_json")
        batch_op.drop_column("source_estimate_hash")
        batch_op.drop_column("source_estimate_workspace_id")
