from tempfile import NamedTemporaryFile

from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.session import engine
from app.services import file_storage
from app.services.file_storage import LocalFileStorageProvider


def _database_readiness() -> tuple[bool, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            inspector = inspect(connection)
            required_tables = ("projects", "documents", "rfq_packages")
            if any(not inspector.has_table(table) for table in required_tables):
                return False, "schema_incomplete"
    except Exception:
        return False, "unavailable"
    return True, "ready"


def _storage_readiness() -> tuple[bool, str]:
    provider = file_storage.storage_provider
    if not isinstance(provider, LocalFileStorageProvider):
        return False, "unsupported"
    try:
        provider.root.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(prefix=".readiness-", dir=provider.root):
            pass
    except OSError:
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
