from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient
import pytest

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.access_control import (
    ModulePermission,
    can_access_module,
    describe_role_access,
)
from app.services.auth import AuthenticatedUser
from app.services.document_audit import (
    clear_recent_document_audit_events,
    list_recent_document_audit_events,
)

client = TestClient(app)


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email=f"{role}@ironhousecivil.com",
            display_name=f"Test {role}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


@pytest.mark.parametrize("role", ["admin", "operations_manager", "estimator", "viewer"])
def test_every_supported_role_can_read_business_modules(role: str) -> None:
    for module in ("projects", "suppliers", "estimates", "documents", "tenders", "equipment"):
        assert can_access_module(role, module, ModulePermission.READ)


def test_role_matrix_separates_administration_and_mutation() -> None:
    assert can_access_module("admin", "users", ModulePermission.ADMINISTER)
    assert not can_access_module("operations_manager", "users", ModulePermission.ADMINISTER)
    assert can_access_module("operations_manager", "equipment", ModulePermission.WRITE)
    assert not can_access_module("estimator", "equipment", ModulePermission.WRITE)
    assert can_access_module("estimator", "estimates", ModulePermission.WRITE)
    assert not can_access_module("viewer", "projects", ModulePermission.WRITE)


def test_viewer_is_read_only_and_denial_is_audited() -> None:
    clear_recent_document_audit_events()
    _authenticate_as("viewer")

    assert client.get("/api/v1/projects").status_code == 200
    response = client.post(
        "/api/v1/projects",
        json={"name": "Viewer must not create this project"},
        headers={"x-request-id": "build-210-viewer-denial"},
    )

    assert response.status_code == 403
    assert "write" in response.json()["detail"]
    event = list_recent_document_audit_events(action="module_access", outcome="denied")[0]
    assert event["actor"] == "viewer@ironhousecivil.com"
    assert event["request_id"] == "build-210-viewer-denial"
    assert event["metadata"] == {
        "module": "projects",
        "permission": "write",
        "method": "POST",
        "path": "/api/v1/projects",
        "role": "viewer",
    }


@pytest.mark.parametrize("role", ["operations_manager", "estimator"])
def test_non_admin_roles_cannot_access_user_administration(role: str) -> None:
    _authenticate_as(role)
    response = client.get("/api/v1/users")
    assert response.status_code == 403
    assert "administer" in response.json()["detail"]


@pytest.mark.parametrize("role", ["admin", "operations_manager", "estimator"])
def test_authorized_business_roles_can_create_projects(role: str) -> None:
    _authenticate_as(role)
    response = client.post(
        "/api/v1/projects",
        json={"name": f"Build 210 {role} project", "project_number": f"B210-{role}"},
    )
    assert response.status_code == 201


def test_permission_summary_is_available_for_the_current_session() -> None:
    _authenticate_as("estimator")
    response = client.get("/api/v1/auth/me/permissions")

    assert response.status_code == 200
    assert response.json() == {
        "role": "estimator",
        "modules": describe_role_access("estimator"),
    }
