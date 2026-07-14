from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser
from app.services.document_audit import (
    DocumentAuditEvent,
    clear_recent_document_audit_events,
    emit_document_audit_event,
)
from app.services.operational_metrics import clear_operational_metrics

client = TestClient(app)


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000213"),
            email=f"{role}@ironhousecivil.com",
            display_name=f"Build 213 {role}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def test_request_id_and_operational_snapshot() -> None:
    clear_operational_metrics()
    response = client.get("/health", headers={"x-request-id": "build-213-health"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "build-213-health"

    _authenticate_as("admin")
    diagnostics = client.get("/api/v1/operations/diagnostics")
    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["readiness"]["service"] == "Iron House OS API"
    assert payload["traffic"]["observed_requests"] >= 1
    assert payload["traffic"]["recent"][0]["request_id"] == "build-213-health"


def test_unsafe_request_id_is_replaced() -> None:
    response = client.get("/health", headers={"x-request-id": "bad\nlog-line"})

    assert response.status_code == 200
    assert response.headers["x-request-id"].startswith("req-")


def test_security_visibility_is_admin_only_and_excludes_business_events() -> None:
    clear_recent_document_audit_events()
    emit_document_audit_event(DocumentAuditEvent(action="login", outcome="denied"))
    emit_document_audit_event(DocumentAuditEvent(action="upload"))

    _authenticate_as("operations_manager")
    assert client.get("/api/v1/operations/security-events").status_code == 403

    _authenticate_as("admin")
    response = client.get("/api/v1/operations/security-events")
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert {item["action"] for item in response.json()["items"]} == {
        "login",
        "module_access",
    }
