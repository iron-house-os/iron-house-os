"""Build 209 complete schema baseline.

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import Inspector
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeEngine

revision = "20260714_0001"
down_revision = None
branch_labels = None
depends_on = None

EXPECTED_SCHEMA: dict[str, set[str]] = {
    "employees": {
        "first_name", "last_name", "email", "role", "auth_subject", "status",
        "id", "created_at", "updated_at",
    },
    "equipment": {
        "name", "equipment_type", "identifier", "status", "hourly_rate",
        "id", "created_at", "updated_at",
    },
    "municipalities": {
        "name", "region", "standards_uri", "notes", "standards_json",
        "id", "created_at", "updated_at",
    },
    "suppliers": {
        "name", "category", "service_area", "website", "notes", "metadata_json",
        "id", "created_at", "updated_at",
    },
    "user_accounts": {
        "email", "display_name", "role", "password_hash", "is_active",
        "session_version", "last_login_at", "id", "created_at", "updated_at",
    },
    "contacts": {
        "supplier_id", "first_name", "last_name", "email", "phone", "role",
        "id", "created_at", "updated_at",
    },
    "projects": {
        "name", "client_owner", "municipality", "project_number", "tender_number",
        "tender_source", "tender_closing_date", "bid_due_date",
        "estimated_construction_start", "estimated_construction_finish",
        "project_address", "latitude", "longitude", "contract_value", "status",
        "municipality_id", "description", "notes", "metadata_json",
        "id", "created_at", "updated_at",
    },
    "drawings": {
        "project_id", "title", "discipline", "revision", "storage_uri",
        "metadata_json", "id", "created_at", "updated_at",
    },
    "project_suppliers": {
        "project_id", "supplier_id", "role", "id", "created_at", "updated_at",
    },
    "rfq_packages": {
        "project_id", "title", "project_name", "scope_summary", "due_at", "status",
        "supplier_category_targets", "metadata_json", "id", "created_at", "updated_at",
    },
    "rfqs": {
        "project_id", "title", "status", "due_at", "scope_summary", "package_json",
        "id", "created_at", "updated_at",
    },
    "quotes": {
        "rfq_id", "supplier_id", "status", "amount", "notes",
        "id", "created_at", "updated_at",
    },
    "rfq_package_documents": {
        "rfq_package_id", "document_type", "title", "required", "status",
        "storage_uri", "metadata_json", "id", "created_at", "updated_at",
    },
    "rfq_package_supplier_recipients": {
        "rfq_package_id", "supplier_id", "supplier_name", "category", "status",
        "id", "created_at", "updated_at",
    },
    "takeoffs": {
        "project_id", "drawing_id", "status", "notes", "quantities_json",
        "id", "created_at", "updated_at",
    },
    "tenders": {
        "municipality_id", "project_id", "rfq_package_id", "title", "tender_number",
        "source", "source_url", "owner", "municipality", "closing_date",
        "site_meeting_date", "question_deadline", "project_address", "description",
        "status", "estimated_value", "metadata_json", "id", "created_at", "updated_at",
    },
    "bids": {
        "project_id", "tender_id", "status", "submitted_at", "total_amount",
        "summary", "bid_json", "id", "created_at", "updated_at",
    },
    "documents": {
        "title", "category", "status", "project_id", "rfq_package_id", "tender_id",
        "supplier_id", "storage_uri", "description", "sheet_number", "drawing_title",
        "discipline", "revision", "issue_date", "metadata_json",
        "id", "created_at", "updated_at",
    },
}


def _json_type() -> TypeEngine:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _id_column() -> sa.Column:
    return sa.Column("id", sa.Uuid(), nullable=False)


def _created_at_column() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def _updated_at_column() -> sa.Column:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def _record_columns() -> tuple[sa.Column, sa.Column, sa.Column]:
    return _id_column(), _created_at_column(), _updated_at_column()


def _validate_build_208_schema(inspector: Inspector) -> bool:
    existing_tables = set(inspector.get_table_names())
    existing_application_tables = existing_tables.intersection(EXPECTED_SCHEMA)
    if not existing_application_tables:
        return False

    missing_tables = sorted(set(EXPECTED_SCHEMA) - existing_tables)
    missing_columns: dict[str, list[str]] = {}
    for table_name, expected_columns in EXPECTED_SCHEMA.items():
        if table_name not in existing_tables:
            continue
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing = sorted(expected_columns - actual_columns)
        if missing:
            missing_columns[table_name] = missing

    if missing_tables or missing_columns:
        details = []
        if missing_tables:
            details.append(f"missing tables: {', '.join(missing_tables)}")
        if missing_columns:
            rendered = "; ".join(
                f"{table}: {', '.join(columns)}"
                for table, columns in sorted(missing_columns.items())
            )
            details.append(f"missing columns: {rendered}")
        raise RuntimeError(
            "Refusing to adopt a partial unversioned (pre-Alembic) schema ("
            + "; ".join(details)
            + "). "
            "Restore a verified Build 208 backup or repair the schema before retrying."
        )
    return True


def _create_schema() -> None:
    op.create_table(
        "employees",
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("auth_subject", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        *_record_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_subject"),
    )
    op.create_index("ix_employees_email", "employees", ["email"], unique=True)

    op.create_table(
        "equipment",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("equipment_type", sa.String(length=120), nullable=True),
        sa.Column("identifier", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(precision=10, scale=2), nullable=True),
        *_record_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_index(
        "ix_equipment_equipment_type",
        "equipment",
        ["equipment_type"],
        unique=False,
    )

    op.create_table(
        "municipalities",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("standards_uri", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("standards_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "suppliers",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("service_area", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suppliers_category", "suppliers", ["category"], unique=False)
    op.create_index("ix_suppliers_name", "suppliers", ["name"], unique=False)

    op.create_table(
        "user_accounts",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("session_version", sa.Integer(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_record_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"], unique=True)

    op.create_table(
        "contacts",
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("role", sa.String(length=120), nullable=True),
        *_record_columns(),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_email", "contacts", ["email"], unique=False)

    op.create_table(
        "projects",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("client_owner", sa.String(length=255), nullable=True),
        sa.Column("municipality", sa.String(length=255), nullable=True),
        sa.Column("project_number", sa.String(length=80), nullable=True),
        sa.Column("tender_number", sa.String(length=120), nullable=True),
        sa.Column("tender_source", sa.String(length=255), nullable=True),
        sa.Column("tender_closing_date", sa.Date(), nullable=True),
        sa.Column("bid_due_date", sa.Date(), nullable=True),
        sa.Column("estimated_construction_start", sa.Date(), nullable=True),
        sa.Column("estimated_construction_finish", sa.Date(), nullable=True),
        sa.Column("project_address", sa.String(length=500), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("contract_value", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("municipality_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["municipality_id"], ["municipalities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_number"),
    )

    op.create_table(
        "drawings",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("discipline", sa.String(length=120), nullable=True),
        sa.Column("revision", sa.String(length=80), nullable=True),
        sa.Column("storage_uri", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "project_suppliers",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        *_record_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "rfq_packages",
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("project_name", sa.String(length=255), nullable=True),
        sa.Column("scope_summary", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("supplier_category_targets", _json_type(), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "rfqs",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope_summary", sa.Text(), nullable=True),
        sa.Column("package_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "quotes",
        sa.Column("rfq_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_record_columns(),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "rfq_package_documents",
        sa.Column("rfq_package_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("storage_uri", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["rfq_package_id"], ["rfq_packages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "rfq_package_supplier_recipients",
        sa.Column("rfq_package_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.String(length=120), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["rfq_package_id"], ["rfq_packages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "takeoffs",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("drawing_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("quantities_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["drawing_id"], ["drawings.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tenders",
        sa.Column("municipality_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("rfq_package_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("tender_number", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("municipality", sa.String(length=255), nullable=True),
        sa.Column("closing_date", sa.Date(), nullable=True),
        sa.Column("site_meeting_date", sa.Date(), nullable=True),
        sa.Column("question_deadline", sa.Date(), nullable=True),
        sa.Column("project_address", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("estimated_value", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["municipality_id"], ["municipalities.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["rfq_package_id"], ["rfq_packages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tender_number"),
    )

    op.create_table(
        "bids",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("tender_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("bid_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("rfq_package_id", sa.Uuid(), nullable=True),
        sa.Column("tender_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("storage_uri", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sheet_number", sa.String(length=80), nullable=True),
        sa.Column("drawing_title", sa.String(length=255), nullable=True),
        sa.Column("discipline", sa.String(length=120), nullable=True),
        sa.Column("revision", sa.String(length=80), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["rfq_package_id"], ["rfq_packages.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_category", "documents", ["category"], unique=False)
    op.create_index("ix_documents_status", "documents", ["status"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    if _validate_build_208_schema(sa.inspect(bind)):
        return
    _create_schema()


def downgrade() -> None:
    raise RuntimeError(
        "The Build 209 baseline cannot be downgraded because it may have adopted a populated "
        "Build 208 database. Restore a verified backup instead."
    )
