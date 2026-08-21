from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser

client = TestClient(app)


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email=f"{role}@ironhousecontracting.com",
            display_name=f"Test {role}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _payload() -> dict:
    return {
        "project_name": "Smith drainage repair",
        "customer_name": "Alex Smith",
        "customer_email": "alex@example.com",
        "customer_phone": "250-555-0100",
        "site_address": "100 Main Street, Chilliwack BC",
        "scope_summary": "Replace failed storm service and restore the driveway.",
        "line_items": [
            {"description": "Excavation and pipe replacement", "quantity": "1", "unit": "LS", "unit_price": "10000.00"},
            {"description": "Driveway restoration", "quantity": "2", "unit": "day", "unit_price": "1000.00"},
        ],
        "assumptions": ["Normal weekday access"],
        "exclusions": ["Contaminated soil disposal"],
        "gst_rate": "5.00",
        "quote_date": "2026-08-21",
        "valid_until": "2026-09-20",
        "notes": "Prepared from customer phone call.",
    }


def _create_quote() -> dict:
    response = client.post("/api/v1/customer-quotes", json=_payload())
    assert response.status_code == 201, response.text
    return response.json()


def test_verbal_quote_creates_a_durable_opportunity_without_job_number() -> None:
    created = _create_quote()

    assert created["quote_number"].startswith("Q-2026-")
    assert created["status"] == "draft"
    assert created["subtotal"] == "12000.00"
    assert created["gst"] == "600.00"
    assert created["total"] == "12600.00"
    assert created["job_number"] is None

    project = client.get(f"/api/v1/projects/{created['project_id']}")
    assert project.status_code == 200
    assert project.json()["status"] == "opportunity"
    assert project.json()["project_number"] is None
    assert project.json()["client_owner"] == "Alex Smith"

    listed = client.get("/api/v1/customer-quotes")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == created["id"]

    pdf = client.get(f"/api/v1/customer-quotes/{created['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_sent_quote_remains_non_binding_and_stale_edits_are_rejected() -> None:
    created = _create_quote()
    sent = client.post(
        f"/api/v1/customer-quotes/{created['id']}/status",
        json={"expected_revision": 1, "status": "sent", "note": "Emailed outside this test."},
    )

    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"
    assert sent.json()["record_revision"] == 2
    assert sent.json()["job_number"] is None

    stale = client.patch(
        f"/api/v1/customer-quotes/{created['id']}",
        json={"expected_revision": 1, "scope_summary": "Stale overwrite"},
    )
    assert stale.status_code == 409
    assert client.get(f"/api/v1/projects/{created['project_id']}").json()["status"] == "opportunity"


def test_management_acceptance_atomically_awards_project_and_is_idempotent() -> None:
    created = _create_quote()
    acceptance = {
        "expected_revision": 1,
        "acceptance_reference": "Customer email received 2026-08-21",
        "acceptance_note": "Proceed at quoted scope and value.",
    }

    accepted = client.post(f"/api/v1/customer-quotes/{created['id']}/accept", json=acceptance)

    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["status"] == "accepted"
    assert body["record_revision"] == 2
    assert body["job_number"].startswith("IH-2026-")
    assert body["accepted_by"] == "test-admin@ironhousecontracting.com"

    project = client.get(f"/api/v1/projects/{created['project_id']}").json()
    assert project["status"] == "awarded"
    assert project["project_number"] == body["job_number"]
    assert project["contract_value"] == 12600.0

    checklist = client.get(f"/api/v1/projects/{created['project_id']}/start-checklist")
    assert checklist.status_code == 200
    assert checklist.json()["total_count"] == 10

    repeated = client.post(f"/api/v1/customer-quotes/{created['id']}/accept", json=acceptance)
    assert repeated.status_code == 200
    assert repeated.json()["job_number"] == body["job_number"]
    assert repeated.json()["record_revision"] == 2


def test_estimator_can_prepare_but_cannot_accept_customer_quote() -> None:
    _authenticate_as("estimator")
    created = _create_quote()

    denied = client.post(
        f"/api/v1/customer-quotes/{created['id']}/accept",
        json={"expected_revision": 1, "acceptance_reference": "Must be management controlled"},
    )

    assert denied.status_code == 403
    assert client.get(f"/api/v1/projects/{created['project_id']}").json()["status"] == "opportunity"


def test_closed_quote_requires_an_editable_revision_before_reopening() -> None:
    created = _create_quote()
    declined = client.post(
        f"/api/v1/customer-quotes/{created['id']}/status",
        json={"expected_revision": 1, "status": "declined", "note": "Customer declined."},
    ).json()

    blocked = client.post(
        f"/api/v1/customer-quotes/{created['id']}/status",
        json={"expected_revision": 2, "status": "sent"},
    )
    assert blocked.status_code == 409

    revised = client.patch(
        f"/api/v1/customer-quotes/{created['id']}",
        json={
            "expected_revision": declined["record_revision"],
            "scope_summary": "Revised scope requested by the customer.",
        },
    )
    assert revised.status_code == 200
    assert revised.json()["status"] == "draft"
    assert revised.json()["record_revision"] == 3


def test_viewer_cannot_read_customer_quote_register() -> None:
    _authenticate_as("viewer")
    response = client.get("/api/v1/customer-quotes")
    assert response.status_code == 403
