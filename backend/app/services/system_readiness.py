from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.schema_version import CURRENT_SCHEMA_REVISION
from app.db.session import engine
from app.services import file_storage


REQUIRED_RUNTIME_TABLES = (
    "alembic_version",
    "bids",
    "contacts",
    "documents",
    "equipment",
    "login_throttles",
    "legal_analyses",
    "legal_audit_events",
    "legal_deadlines",
    "legal_matters",
    "municipalities",
    "projects",
    "project_suppliers",
    "quotes",
    "rfq_packages",
    "rfq_package_documents",
    "rfq_package_supplier_recipients",
    "rfqs",
    "suppliers",
    "takeoffs",
    "tenders",
    "user_accounts",
)
VALID_TENDER_STATUSES = (
    "new",
    "reviewing",
    "bidding",
    "submitted",
    "awarded",
    "lost",
    "no_bid",
)
WORKFLOW_VALUE_CHECKS = (
    (
        "project_status",
        "projects",
        "status",
        ("opportunity", "tendering", "awarded", "construction", "completed", "archived"),
    ),
    (
        "document_category",
        "documents",
        "category",
        (
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
        ),
    ),
    (
        "document_status",
        "documents",
        "status",
        ("registered", "active", "current", "superseded", "archived"),
    ),
    (
        "rfq_package_status",
        "rfq_packages",
        "status",
        ("draft", "assembling", "ready", "issued", "closed"),
    ),
    (
        "rfq_recipient_status",
        "rfq_package_supplier_recipients",
        "status",
        ("pending", "sent", "replied", "bounced"),
    ),
    (
        "rfq_document_status",
        "rfq_package_documents",
        "status",
        ("pending", "attached", "not_applicable"),
    ),
    (
        "equipment_status",
        "equipment",
        "status",
        ("available", "reserved", "in_use", "maintenance", "retired"),
    ),
    (
        "user_role",
        "user_accounts",
        "role",
        ("admin", "operations_manager", "estimator", "viewer"),
    ),
    ("tender_status", "tenders", "status", VALID_TENDER_STATUSES),
)


def _database_readiness() -> tuple[bool, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            inspector = inspect(connection)
            if any(not inspector.has_table(table) for table in REQUIRED_RUNTIME_TABLES):
                return False, "schema_incomplete"
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if revision != CURRENT_SCHEMA_REVISION:
                return False, "migration_required"
            for check_name, table, column, valid_values in WORKFLOW_VALUE_CHECKS:
                parameters = {f"value_{index}": value for index, value in enumerate(valid_values)}
                placeholders = ", ".join(f":value_{index}" for index in range(len(valid_values)))
                invalid_value = connection.execute(
                    text(f"SELECT 1 FROM {table} WHERE {column} IS NULL OR {column} NOT IN ({placeholders}) LIMIT 1"),
                    parameters,
                ).scalar()
                if invalid_value is not None:
                    return False, f"invalid_{check_name}"
    except Exception:
        return False, "unavailable"
    return True, "ready"


def _storage_readiness() -> tuple[bool, str]:
    provider = file_storage.storage_provider
    try:
        provider.readiness_check()
    except (OSError, RuntimeError):
        return False, "unavailable"
    return True, "ready"


def get_system_readiness(*, probe_runtime: bool = False) -> dict[str, object]:
    settings = get_settings()
    checks = {
        "api_router": "mounted",
        "cors": "configured",
        "docs": "enabled",
        "project_workspace": "enabled",
        "document_library": "enabled",
        "civil_pdf_ingestion": "enabled",
        "drawing_quantity_candidates": "enabled",
        "drawing_review_flags": "enabled",
        "takeoff_engine": "enabled",
        "takeoff_persistence": "enabled",
        "estimate_handoff": "enabled",
        "estimate_workspace": "enabled",
        "rfq_linkage": "enabled",
        "project_readiness": "enabled",
        "user_session_authentication": "enabled",
        "deployment_environment": settings.environment,
        "release_id": settings.release_id,
    }
    ready = True
    if probe_runtime:
        database_ready, checks["database"] = _database_readiness()
        storage_ready, checks["document_storage"] = _storage_readiness()
        ready = database_ready and storage_ready

    return {
        "status": "ready" if ready else "not_ready",
        "service": settings.app_name,
        "api_prefix": settings.api_v1_prefix,
        "checks": checks,
    }
