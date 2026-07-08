from app.core.config import get_settings


def get_system_readiness() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ready",
        "service": settings.app_name,
        "api_prefix": settings.api_v1_prefix,
        "checks": {
            "api_router": "mounted",
            "cors": "configured",
            "docs": "enabled",
            "project_workspace": "enabled",
            "document_library": "enabled",
            "takeoff_engine": "enabled",
            "takeoff_persistence": "enabled",
            "estimate_handoff": "enabled",
            "estimate_workspace": "enabled",
            "rfq_linkage": "enabled",
            "project_readiness": "enabled",
        },
    }
