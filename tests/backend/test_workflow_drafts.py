from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser

client = TestClient(app)
OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_OWNER_ID = UUID("00000000-0000-0000-0000-000000000002")


def _authenticate_as(account_id: UUID, role: str = "viewer") -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=account_id,
            email=f"{account_id}@ironhousecontracting.com",
            display_name="Draft Owner",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _create_draft(title: str = "PO for test project") -> dict:
    response = client.post(
        "/api/v1/workflow-drafts",
        json={
            "workflow_type": "purchase_order_request",
            "title": title,
            "payload": {"purpose": "Pipe and fittings", "amount": "1250.00"},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_viewer_can_create_list_read_and_update_only_their_draft() -> None:
    _authenticate_as(OWNER_ID)
    created = _create_draft()

    assert created["owner_account_id"] == str(OWNER_ID)
    assert created["revision"] == 1
    assert created["status"] == "active"

    listed = client.get("/api/v1/workflow-drafts")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == created["id"]

    updated = client.patch(
        f"/api/v1/workflow-drafts/{created['id']}",
        json={
            "expected_revision": 1,
            "title": "Updated PO draft",
            "payload": {"purpose": "Pipe, fittings, and valves", "amount": "1500.00"},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert updated.json()["title"] == "Updated PO draft"
    assert updated.json()["payload"]["amount"] == "1500.00"

    _authenticate_as(OTHER_OWNER_ID)
    assert client.get(f"/api/v1/workflow-drafts/{created['id']}").status_code == 404
    assert client.patch(
        f"/api/v1/workflow-drafts/{created['id']}",
        json={"expected_revision": 2, "payload": {"tampered": True}},
    ).status_code == 404
    assert client.get("/api/v1/workflow-drafts").json() == {"items": [], "total": 0}


def test_stale_revision_returns_conflict_without_overwriting_newer_work() -> None:
    _authenticate_as(OWNER_ID)
    created = _create_draft()

    first = client.patch(
        f"/api/v1/workflow-drafts/{created['id']}",
        json={"expected_revision": 1, "payload": {"version": "newer"}},
    )
    stale = client.patch(
        f"/api/v1/workflow-drafts/{created['id']}",
        json={"expected_revision": 1, "payload": {"version": "stale"}},
    )

    assert first.status_code == 200
    assert stale.status_code == 409
    persisted = client.get(f"/api/v1/workflow-drafts/{created['id']}").json()
    assert persisted["revision"] == 2
    assert persisted["payload"] == {"version": "newer"}


def test_cancel_is_soft_and_excluded_from_resume_list() -> None:
    _authenticate_as(OWNER_ID)
    created = _create_draft()

    cancelled = client.post(
        f"/api/v1/workflow-drafts/{created['id']}/cancel",
        json={"expected_revision": 1},
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["revision"] == 2
    assert client.get("/api/v1/workflow-drafts").json() == {"items": [], "total": 0}

    audit_view = client.get("/api/v1/workflow-drafts?include_cancelled=true")
    assert audit_view.status_code == 200
    assert audit_view.json()["items"][0]["status"] == "cancelled"


def test_completed_draft_leaves_resume_list_but_remains_auditable() -> None:
    _authenticate_as(OWNER_ID)
    created = _create_draft()

    completed = client.post(
        f"/api/v1/workflow-drafts/{created['id']}/complete",
        json={"expected_revision": 1},
    )

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert client.get("/api/v1/workflow-drafts").json()["total"] == 0
    assert client.get(
        "/api/v1/workflow-drafts?include_cancelled=true",
    ).json()["items"][0]["status"] == "completed"


def test_invalid_workflow_type_is_rejected() -> None:
    _authenticate_as(OWNER_ID)
    response = client.post(
        "/api/v1/workflow-drafts",
        json={"workflow_type": "approval", "title": "Must not become a commitment"},
    )
    assert response.status_code == 422
