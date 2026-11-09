"""Build 220 field operations and fleet foundation.

Revision ID: 20260722_0005
Revises: 20260721_0004
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid import UUID

revision = "20260722_0005"
down_revision = "20260721_0004"
branch_labels = None
depends_on = None


def _json_type():
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _record_columns():
    return (
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    # A complete pre-Alembic/current schema may already contain this build when
    # the baseline migration adopts it. In that case Alembic only needs to
    # record the revision; recreating the tables would destroy or duplicate data.
    if "vehicles" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    for column in (
        sa.Column("phone", sa.String(80)),
        sa.Column("address", sa.String(500)),
        sa.Column("emergency_contact_name", sa.String(255)),
        sa.Column("emergency_contact_phone", sa.String(80)),
        sa.Column("emergency_contact_relationship", sa.String(120)),
        sa.Column("hire_date", sa.Date()),
        sa.Column("portal_role", sa.String(40), server_default="employee", nullable=False),
        sa.Column("notes", sa.Text()),
    ):
        op.add_column("employees", column)

    op.create_table(
        "vehicles",
        sa.Column("unit_number", sa.String(40), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("assigned_driver_name", sa.String(255)),
        sa.Column("assigned_employee_id", sa.Uuid()),
        sa.Column("make", sa.String(120)),
        sa.Column("model", sa.String(120)),
        sa.Column("year", sa.Integer()),
        sa.Column("vin", sa.String(40)),
        sa.Column("licence_plate", sa.String(40)),
        sa.Column("current_km", sa.Float(), server_default="0", nullable=False),
        sa.Column("next_service_km", sa.Float()),
        sa.Column("next_service_date", sa.Date()),
        sa.Column("status", sa.String(40), server_default="active", nullable=False),
        sa.Column("notes", sa.Text()),
        *_record_columns(),
        sa.ForeignKeyConstraint(["assigned_employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unit_number"),
        sa.UniqueConstraint("vin"),
    )
    op.create_index("ix_vehicles_unit_number", "vehicles", ["unit_number"], unique=True)

    op.create_table(
        "vehicle_logs",
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid()),
        sa.Column("project_id", sa.Uuid()),
        sa.Column("log_type", sa.String(40), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("odometer_km", sa.Float()),
        sa.Column("litres", sa.Float()),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("vendor", sa.String(255)),
        sa.Column("details", sa.Text()),
        sa.Column("document_ids", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("vehicle_id", "log_type", "entry_date"):
        op.create_index(f"ix_vehicle_logs_{column}", "vehicle_logs", [column])

    op.create_table(
        "employee_certifications",
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(255)),
        sa.Column("certificate_number", sa.String(120)),
        sa.Column("issued_date", sa.Date()),
        sa.Column("expiry_date", sa.Date()),
        sa.Column("document_id", sa.Uuid()),
        sa.Column("notes", sa.Text()),
        *_record_columns(),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_certifications_employee_id", "employee_certifications", ["employee_id"])
    op.create_index("ix_employee_certifications_expiry_date", "employee_certifications", ["expiry_date"])

    op.create_table(
        "time_entries",
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("cost_code", sa.String(32), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("regular_hours", sa.Float(), server_default="0", nullable=False),
        sa.Column("overtime_hours", sa.Float(), server_default="0", nullable=False),
        sa.Column("entry_type", sa.String(40), server_default="employee", nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(40), server_default="submitted", nullable=False),
        sa.Column("submitted_by", sa.String(255)),
        *_record_columns(),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("employee_id", "project_id", "cost_code", "work_date"):
        op.create_index(f"ix_time_entries_{column}", "time_entries", [column])

    op.create_table(
        "field_records",
        sa.Column("record_type", sa.String(80), nullable=False),
        sa.Column("project_id", sa.Uuid()),
        sa.Column("employee_id", sa.Uuid()),
        sa.Column("equipment_id", sa.Uuid()),
        sa.Column("supplier_id", sa.Uuid()),
        sa.Column("cost_code", sa.String(32)),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(40), server_default="submitted", nullable=False),
        sa.Column("severity", sa.String(40), server_default="none", nullable=False),
        sa.Column("details", _json_type(), nullable=False),
        sa.Column("document_ids", _json_type(), nullable=False),
        sa.Column("signatures", _json_type(), nullable=False),
        sa.Column("alert_recipients", _json_type(), nullable=False),
        sa.Column("submitted_by", sa.String(255)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *_record_columns(),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("record_type", "project_id", "employee_id", "cost_code", "work_date"):
        op.create_index(f"ix_field_records_{column}", "field_records", [column])

    vehicles = sa.table(
        "vehicles",
        sa.column("id", sa.Uuid()),
        sa.column("unit_number", sa.String()),
        sa.column("name", sa.String()),
        sa.column("assigned_driver_name", sa.String()),
        sa.column("make", sa.String()),
        sa.column("model", sa.String()),
        sa.column("current_km", sa.Float()),
        sa.column("status", sa.String()),
    )
    op.bulk_insert(vehicles, [
        {"id": UUID("00000000-0000-4000-8000-000000000001"), "unit_number": "001", "name": "Mac GMC 3500 Truck", "assigned_driver_name": "Mac Warren", "make": "GMC", "model": "3500", "current_km": 0, "status": "active"},
        {"id": UUID("00000000-0000-4000-8000-000000000002"), "unit_number": "002", "name": "Jeremie GMC 3500 Truck", "assigned_driver_name": "Jeremie Peters", "make": "GMC", "model": "3500", "current_km": 0, "status": "active"},
    ])


def downgrade() -> None:
    op.drop_table("field_records")
    op.drop_table("time_entries")
    op.drop_table("employee_certifications")
    op.drop_table("vehicle_logs")
    op.drop_table("vehicles")
    for column in (
        "notes", "portal_role", "hire_date", "emergency_contact_relationship",
        "emergency_contact_phone", "emergency_contact_name", "address", "phone",
    ):
        op.drop_column("employees", column)
