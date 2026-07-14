from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.schema_version import CURRENT_SCHEMA_REVISION
from app.db.session import engine
from app.services import file_storage


def _database_readiness() -> tuple[bool, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            inspector = inspect(connection)
            required_tables = (
                "projects",
                "documents",
                "rfq_packages",
                "user_accounts",
                "login_throttles",
                "alembic_version",
            )
            if any(not inspector.has_table(table) for table in required_tables):
                return False, "schema_incomplete"
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if revision != CURRENT_SCHEMA_REVISION:
                return False, "migration_required"
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
