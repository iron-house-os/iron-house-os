"""Normalize every enum-backed workflow value adopted from pre-Alembic data.

Revision ID: 20260721_0004
Revises: 20260721_0003
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0004"
down_revision = "20260721_0003"
branch_labels = None
depends_on = None

PROJECT_STATUSES = (
    "opportunity",
    "tendering",
    "awarded",
    "construction",
    "completed",
    "archived",
)
DOCUMENT_CATEGORIES = (
    "drawing",
    "specification",
    "addendum",
    "geotechnical",
    "permit",
    "traffic_control",
    "environmental",
    "quote_request",
    "quote",
    "photo",
    "testing",
    "other",
)
DOCUMENT_STATUSES = ("registered", "active", "current", "superseded", "archived")
RFQ_PACKAGE_STATUSES = ("draft", "assembling", "ready", "issued", "closed")
RFQ_RECIPIENT_STATUSES = ("pending", "sent", "replied", "bounced")
RFQ_DOCUMENT_STATUSES = ("pending", "attached", "not_applicable")
EQUIPMENT_STATUSES = ("available", "reserved", "in_use", "maintenance", "retired")
USER_ROLES = ("admin", "operations_manager", "estimator", "viewer")


def _constraint_values(values: tuple[str, ...]) -> str:
    return ", ".join(repr(value) for value in values)


def upgrade() -> None:
    for table, column in (
        ("projects", "status"),
        ("documents", "category"),
        ("documents", "status"),
        ("rfq_packages", "status"),
        ("rfq_package_supplier_recipients", "status"),
        ("rfq_package_documents", "status"),
        ("equipment", "status"),
        ("user_accounts", "role"),
    ):
        op.execute(
            sa.text(
                f"UPDATE {table} SET {column} = lower(trim({column})) "
                f"WHERE {column} IS NOT NULL AND {column} <> lower(trim({column}))"
            )
        )

    op.execute(
        sa.text(
            """
            UPDATE projects
            SET status = CASE
                WHEN lower(trim(coalesce(status, ''))) IN ('planning', 'draft') THEN 'opportunity'
                WHEN lower(trim(coalesce(status, ''))) IN ('open', 'bidding', 'tender') THEN 'tendering'
                WHEN lower(trim(coalesce(status, ''))) IN ('won') THEN 'awarded'
                WHEN lower(trim(coalesce(status, ''))) IN ('active', 'in progress', 'in_progress') THEN 'construction'
                WHEN lower(trim(coalesce(status, ''))) IN ('complete', 'closed') THEN 'completed'
                ELSE 'opportunity'
            END
            WHERE status IS NULL
               OR lower(trim(status)) NOT IN ('opportunity', 'tendering', 'awarded', 'construction', 'completed', 'archived')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE equipment
            SET status = CASE
                WHEN lower(trim(coalesce(status, ''))) IN ('operational', 'ready') THEN 'available'
                WHEN lower(trim(coalesce(status, ''))) IN ('active', 'working', 'deployed') THEN 'in_use'
                WHEN lower(trim(coalesce(status, ''))) IN ('repair', 'out of service', 'out_of_service') THEN 'maintenance'
                WHEN lower(trim(coalesce(status, ''))) IN ('sold', 'disposed') THEN 'retired'
                ELSE 'maintenance'
            END
            WHERE status IS NULL
               OR lower(trim(status)) NOT IN ('available', 'reserved', 'in_use', 'maintenance', 'retired')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE user_accounts
            SET role = CASE
                WHEN lower(trim(coalesce(role, ''))) IN ('administrator') THEN 'admin'
                WHEN lower(trim(coalesce(role, ''))) IN ('manager', 'project manager', 'project_manager', 'operations') THEN 'operations_manager'
                WHEN lower(trim(coalesce(role, ''))) IN ('estimating') THEN 'estimator'
                ELSE 'viewer'
            END
            WHERE role IS NULL
               OR lower(trim(role)) NOT IN ('admin', 'operations_manager', 'estimator', 'viewer')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET category = CASE
                WHEN lower(trim(coalesce(category, ''))) IN ('drawing', 'drawings', 'plan', 'plans') THEN 'drawing'
                WHEN lower(trim(coalesce(category, ''))) IN ('spec', 'specs', 'specification', 'specifications') THEN 'specification'
                WHEN lower(trim(coalesce(category, ''))) IN ('addendum', 'addenda') THEN 'addendum'
                WHEN lower(trim(coalesce(category, ''))) IN ('geotech', 'geotechnical') THEN 'geotechnical'
                WHEN lower(trim(coalesce(category, ''))) IN ('permit', 'permits') THEN 'permit'
                WHEN lower(trim(coalesce(category, ''))) IN ('traffic', 'traffic-control', 'traffic control', 'traffic_control') THEN 'traffic_control'
                WHEN lower(trim(coalesce(category, ''))) IN ('environment', 'environmental') THEN 'environmental'
                WHEN lower(trim(coalesce(category, ''))) IN ('rfq', 'quote request', 'quote-request', 'quote_request', 'quote_requests') THEN 'quote_request'
                WHEN lower(trim(coalesce(category, ''))) IN ('quote', 'quotes') THEN 'quote'
                WHEN lower(trim(coalesce(category, ''))) IN ('photo', 'photos', 'image', 'images') THEN 'photo'
                WHEN lower(trim(coalesce(category, ''))) IN ('test', 'tests', 'testing', 'inspection') THEN 'testing'
                ELSE 'other'
            END
            WHERE category IS NULL
               OR lower(trim(category)) NOT IN ('drawing', 'specification', 'addendum', 'geotechnical', 'permit', 'traffic_control', 'environmental', 'quote_request', 'quote', 'photo', 'testing', 'other')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET status = CASE
                WHEN lower(trim(coalesce(status, ''))) IN ('pending', 'draft', 'indexed', 'uploaded') THEN 'registered'
                WHEN lower(trim(coalesce(status, ''))) IN ('live') THEN 'active'
                WHEN lower(trim(coalesce(status, ''))) IN ('approved') THEN 'current'
                WHEN lower(trim(coalesce(status, ''))) IN ('obsolete') THEN 'superseded'
                WHEN lower(trim(coalesce(status, ''))) IN ('deleted') THEN 'archived'
                ELSE 'registered'
            END
            WHERE status IS NULL
               OR lower(trim(status)) NOT IN ('registered', 'active', 'current', 'superseded', 'archived')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE rfq_packages
            SET status = CASE
                WHEN lower(trim(coalesce(status, ''))) IN ('planning') THEN 'draft'
                WHEN lower(trim(coalesce(status, ''))) IN ('open', 'in progress', 'in_progress') THEN 'assembling'
                WHEN lower(trim(coalesce(status, ''))) IN ('complete', 'approved') THEN 'ready'
                WHEN lower(trim(coalesce(status, ''))) IN ('sent') THEN 'issued'
                WHEN lower(trim(coalesce(status, ''))) IN ('archived') THEN 'closed'
                ELSE 'draft'
            END
            WHERE status IS NULL
               OR lower(trim(status)) NOT IN ('draft', 'assembling', 'ready', 'issued', 'closed')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE rfq_package_supplier_recipients
            SET status = CASE
                WHEN lower(trim(coalesce(status, ''))) IN ('selected', 'requested') THEN 'pending'
                WHEN lower(trim(coalesce(status, ''))) IN ('responded') THEN 'replied'
                ELSE 'pending'
            END
            WHERE status IS NULL
               OR lower(trim(status)) NOT IN ('pending', 'sent', 'replied', 'bounced')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE rfq_package_documents
            SET status = CASE
                WHEN lower(trim(coalesce(status, ''))) IN ('excluded', 'n/a', 'n_a') THEN 'not_applicable'
                WHEN storage_uri IS NOT NULL AND trim(storage_uri) <> '' THEN 'attached'
                ELSE 'pending'
            END
            WHERE status IS NULL
               OR lower(trim(status)) NOT IN ('pending', 'attached', 'not_applicable')
            """
        )
    )

    constraints = (
        ("projects", "ck_projects_status", "status", PROJECT_STATUSES),
        ("documents", "ck_documents_category", "category", DOCUMENT_CATEGORIES),
        ("documents", "ck_documents_status", "status", DOCUMENT_STATUSES),
        ("rfq_packages", "ck_rfq_packages_status", "status", RFQ_PACKAGE_STATUSES),
        (
            "rfq_package_supplier_recipients",
            "ck_rfq_package_recipients_status",
            "status",
            RFQ_RECIPIENT_STATUSES,
        ),
        (
            "rfq_package_documents",
            "ck_rfq_package_documents_status",
            "status",
            RFQ_DOCUMENT_STATUSES,
        ),
        ("equipment", "ck_equipment_status", "status", EQUIPMENT_STATUSES),
        ("user_accounts", "ck_user_accounts_role", "role", USER_ROLES),
    )
    for table, name, column, values in constraints:
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_check_constraint(
                name,
                f"{column} IN ({_constraint_values(values)})",
            )


def downgrade() -> None:
    constraints = (
        ("user_accounts", "ck_user_accounts_role"),
        ("equipment", "ck_equipment_status"),
        ("rfq_package_documents", "ck_rfq_package_documents_status"),
        ("rfq_package_supplier_recipients", "ck_rfq_package_recipients_status"),
        ("rfq_packages", "ck_rfq_packages_status"),
        ("documents", "ck_documents_status"),
        ("documents", "ck_documents_category"),
        ("projects", "ck_projects_status"),
    )
    for table, name in constraints:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(name, type_="check")
