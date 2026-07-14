from typing import Any

from fastapi import APIRouter

from app.api.dependencies.auth import AdminUser
from app.services.document_audit import list_recent_document_audit_events, summarize_document_audit_events
from app.services.operational_metrics import operational_snapshot
from app.services.system_readiness import get_system_readiness

router = APIRouter()
SECURITY_ACTIONS = {
    "account_recovery",
    "login",
    "module_access",
    "password_change",
}


@router.get("/diagnostics")
def operational_diagnostics(_: AdminUser) -> dict[str, Any]:
    return {
        "readiness": get_system_readiness(probe_runtime=True),
        "traffic": operational_snapshot(),
        "audit": summarize_document_audit_events(),
    }


@router.get("/security-events")
def security_events(_: AdminUser, limit: int = 50) -> dict[str, Any]:
    events = list_recent_document_audit_events(limit=200)
    selected = [event for event in events if event.get("action") in SECURITY_ACTIONS]
    bounded_limit = max(1, min(limit, 100))
    return {"items": selected[:bounded_limit], "total": len(selected)}
