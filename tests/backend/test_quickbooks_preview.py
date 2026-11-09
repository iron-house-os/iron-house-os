from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.finance import CustomerInvoice
from app.services.auth import AuthenticatedUser
from conftest import TestingSessionLocal

client = TestClient(app)


def _invoice(project_id: str | None = None) -> dict:
    payload = {
        "invoice_number": "QB-PREVIEW-1",
        "project_name": "Real job",
        "customer_name": "Customer",
        "customer_address": "123 Main Street",
        "invoice_date": "2026-09-01",
        "due_date": "2026-10-01",
        "gst_rate": "5",
        "line_items": [
            {"description": "Civil work", "quantity": "3", "unit_price": "0.10"},
            {"description": "Second line", "quantity": "1", "unit_price": "0.20"},
        ],
    }
    if project_id:
        payload["project_id"] = project_id
    return client.post("/api/v1/finance/customer-invoices", json=payload).json()


def _preview(invoice: dict):
    return client.get(f"/api/v1/finance/customer-invoices/{invoice['id']}/quickbooks-preview")


def test_preview_requires_real_issued_invoice_and_does_not_export() -> None:
    project = client.post("/api/v1/projects", json={"name": "Real job", "status": "awarded"}).json()
    invoice = _invoice(project["id"])
    draft = _preview(invoice)
    assert draft.status_code == 200
    assert draft.json()["source_checks_passed"] is False
    assert draft.json()["export_enabled"] is False

    client.patch(f"/api/v1/finance/customer-invoices/{invoice['id']}/status", json={"status": "approved"})
    client.patch(f"/api/v1/finance/customer-invoices/{invoice['id']}/status", json={"status": "issued"})
    ready = _preview(invoice)
    assert ready.status_code == 200
    assert ready.json()["source_checks_passed"] is True
    assert ready.json()["export_enabled"] is False
    assert ready.json()["subtotal"] == "0.50"
    assert ready.json()["gst"] == "0.03"
    assert ready.json()["total"] == "0.53"
    assert ready.json()["line_items"][0]["amount"] == "0.30"
    assert len(ready.json()["accounting_setup_required"]) == 4


def test_unlinked_invoice_and_development_seed_are_blocked() -> None:
    invoice = _invoice()
    result = _preview(invoice).json()
    assert any("Link the invoice" in text for text in result["blockers"])
    seed = next(item for item in client.get("/api/v1/finance/customer-invoices").json()["items"]
                if item["development_seed_key"])
    seed_result = _preview(seed).json()
    assert any("Development seed" in text for text in seed_result["blockers"])


def test_tampered_invoice_tax_cannot_pass_source_checks() -> None:
    project = client.post("/api/v1/projects", json={"name": "Tax check", "status": "awarded"}).json()
    invoice = _invoice(project["id"])
    client.patch(f"/api/v1/finance/customer-invoices/{invoice['id']}/status", json={"status": "approved"})
    client.patch(f"/api/v1/finance/customer-invoices/{invoice['id']}/status", json={"status": "issued"})
    with TestingSessionLocal() as db:
        row = db.get(CustomerInvoice, UUID(invoice["id"]))
        row.gst = 1
        db.commit()
    result = _preview(invoice)
    assert result.status_code == 200
    assert not result.json()["source_checks_passed"]
    assert not result.json()["export_enabled"]
    assert any("reconcile exactly" in text for text in result.json()["blockers"])


def test_preview_is_management_only() -> None:
    invoice = _invoice()

    def viewer(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000099"),
            email="viewer@example.com",
            display_name="Viewer",
            role="viewer",
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = viewer
    assert _preview(invoice).status_code == 403
