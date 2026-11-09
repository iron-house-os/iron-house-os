from datetime import date
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser

client = TestClient(app)


def _payload() -> dict:
    return {
        "invoice_number": "TEST-1001",
        "project_name": "Decimal-safe test",
        "site_address": "100 Test Road",
        "customer_name": "Test Customer",
        "customer_address": "200 Customer Street",
        "invoice_date": "2026-08-16",
        "due_date": "2026-09-15",
        "terms": "Net 30",
        "gst_rate": "5",
        "line_items": [
            {"description": "Fractional quantity", "quantity": "3", "unit_price": "0.10"},
            {"description": "Second line", "quantity": "1", "unit_price": "0.20"},
        ],
    }


def test_invoice_calculation_persistence_and_pdf() -> None:
    created = client.post("/api/v1/finance/customer-invoices", json=_payload())
    assert created.status_code == 201
    invoice = created.json()
    assert invoice["subtotal"] == "0.50"
    assert invoice["gst"] == "0.03"
    assert invoice["total"] == "0.53"

    read = client.get(f"/api/v1/finance/customer-invoices/{invoice['id']}")
    assert read.status_code == 200
    assert read.json()["line_items"][0]["amount"] == "0.30"

    pdf = client.get(f"/api/v1/finance/customer-invoices/{invoice['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-1.4")


def test_invoice_status_controls_require_approval_before_issue() -> None:
    invoice = client.post("/api/v1/finance/customer-invoices", json=_payload()).json()
    blocked = client.patch(
        f"/api/v1/finance/customer-invoices/{invoice['id']}/status", json={"status": "issued"}
    )
    assert blocked.status_code == 409
    approved = client.patch(
        f"/api/v1/finance/customer-invoices/{invoice['id']}/status", json={"status": "approved"}
    )
    assert approved.status_code == 200
    issued = client.patch(
        f"/api/v1/finance/customer-invoices/{invoice['id']}/status", json={"status": "issued"}
    )
    assert issued.status_code == 200
    assert issued.json()["issued_by"] == "test-admin@ironhousecontracting.com"


def test_development_seeds_include_verified_bennett_and_bowline_records() -> None:
    response = client.get("/api/v1/finance/customer-invoices")
    assert response.status_code == 200
    by_key = {item["development_seed_key"]: item for item in response.json()["items"]}
    assert by_key["bennett-road"]["total"] == "12334.71"
    assert by_key["bowline-common-excavation"]["subtotal"] == "8690.00"
    assert by_key["bowline-common-excavation"]["total"] == "9124.50"
    assert by_key["bowline-common-excavation"]["site_address"] is None


def test_customer_invoice_api_is_denied_to_non_management() -> None:
    def viewer(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000099"), email="viewer@example.com",
            display_name="Viewer", role="viewer", session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = viewer
    assert client.get("/api/v1/finance/customer-invoices").status_code == 403


def test_invoice_rejects_due_date_before_invoice_date() -> None:
    payload = _payload()
    payload["invoice_date"] = str(date(2026, 9, 1))
    payload["due_date"] = str(date(2026, 8, 31))
    assert client.post("/api/v1/finance/customer-invoices", json=payload).status_code == 422
