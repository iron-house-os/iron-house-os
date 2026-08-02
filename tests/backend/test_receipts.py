from datetime import date
from uuid import UUID

import csv
import io
import json
from types import SimpleNamespace

import pytest

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.finance import CompanyCard, ReceiptAlias
from app.models.supplier import Supplier
from app.services.auth import AuthenticatedUser
from app.services.file_storage import LocalFileStorageProvider
import app.services.file_storage as file_storage
import app.services.receipt_extraction as receipt_extraction
import app.services.receipts as receipt_service
from conftest import TestingSessionLocal

client = TestClient(app)


@pytest.fixture(autouse=True)
def receipt_storage(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))


def _project(number: str = "RCPT-114") -> dict:
    response = client.post("/api/v1/projects", json={"name": "Receipt Coding Job", "project_number": number})
    assert response.status_code == 201
    return response.json()


def _asset(content: bytes = b"receipt-image-one") -> str:
    response = client.post(
        "/api/v1/media",
        data={"category": "receipt", "caption": "Receipt evidence"},
        files={"files": ("receipt.jpg", content, "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    return response.json()[0]["id"]


def _payload(asset_id: str, project_id: str, *, confidence: float = 0.98, balanced: bool = True) -> dict:
    return {
        "media_asset_ids": [asset_id], "vendor_name": "Home Hardware", "vendor_address": "100 Main St",
        "reference": "R-114-001", "receipt_date": str(date.today()), "receipt_time": "08:14", "currency": "CAD",
        "subtotal": 100, "discounts": 0, "gst": 5, "pst": 0, "other_tax": 0, "tip": 0,
        "total": 105 if balanced else 110, "payment_method": "card", "card_brand": "Visa", "card_last_four": "4242",
        "employee_email": "crew@ironhousecontracting.com", "treatment": "company_card",
        "confidence": {"vendor_name": confidence, "receipt_date": confidence, "subtotal": confidence, "total": confidence},
        "source_regions": {"total": {"page": 1, "x": 0.6, "y": 0.8, "width": 0.3, "height": 0.08}}, "flags": [],
        "line_items": [
            {"description": "GRN NITRILE GLV", "normalized_description": "Green nitrile safety gloves", "quantity": 2, "unit_price": 30, "tax": 3, "line_total": 60, "category": "ppe", "project_id": project_id, "cost_code": "01-120", "treatment": "company_card", "confidence": confidence, "source_region": {"page": 1, "x": 0.1, "y": 0.35, "width": 0.7, "height": 0.06}, "flags": []},
            {"description": "Printer paper", "normalized_description": "Printer paper", "quantity": 1, "unit_price": 40, "tax": 2, "line_total": 40, "category": "office_admin", "overhead_category": "office_admin", "treatment": "company_card", "confidence": confidence, "flags": []},
        ],
    }


def _seed_vendor_and_card() -> tuple[UUID, UUID]:
    with TestingSessionLocal() as db:
        supplier = Supplier(name="Home Hardware", category="tools", metadata_json={})
        card = CompanyCard(brand="Visa", last_four="4242", holder_email="crew@ironhousecontracting.com", label="Crew card", is_authorized=True)
        db.add_all([supplier, card])
        db.commit()
        db.refresh(supplier)
        db.refresh(card)
        return supplier.id, card.id


def test_split_coding_vendor_card_alias_approval_and_one_time_export(monkeypatch) -> None:
    project = _project()
    vendor_id, card_id = _seed_vendor_and_card()
    created = client.post("/api/v1/finance/receipts", json=_payload(_asset(), project["id"]))
    assert created.status_code == 201, created.text
    receipt = created.json()
    assert receipt["vendor_id"] == str(vendor_id)
    assert receipt["company_card_id"] == str(card_id)
    assert receipt["is_balanced"] is True
    assert {line["project_id"] for line in receipt["line_items"]} == {project["id"], None}

    locked_calls = []
    original_locked_lookup = receipt_service._require_receipt_for_update

    def tracked_locked_lookup(*args, **kwargs):
        locked_calls.append(args[1])
        return original_locked_lookup(*args, **kwargs)

    monkeypatch.setattr(receipt_service, "_require_receipt_for_update", tracked_locked_lookup)
    submitted = client.post(f"/api/v1/finance/receipts/{receipt['id']}/submit", json={"version": receipt["version"], "reason": "Employee confirmed receipt"})
    assert submitted.status_code == 200
    receipt = submitted.json()
    approved = client.post(f"/api/v1/finance/receipts/{receipt['id']}/approve", json={"version": receipt["version"], "reason": "Reviewer verified original, coding, tax, and card"})
    assert approved.status_code == 200, approved.text
    receipt = approved.json()
    assert receipt["status"] == "approved"
    with TestingSessionLocal() as db:
        alias = db.scalar(select(ReceiptAlias).where(ReceiptAlias.vendor_id == vendor_id))
        assert alias is not None
        assert alias.normalized_value == "Green nitrile safety gloves"

    exported = client.post(f"/api/v1/finance/receipts/{receipt['id']}/export", json={"version": receipt["version"], "reason": "QB staging batch 114"})
    assert exported.status_code == 200
    assert "Green nitrile safety gloves" in exported.text
    export_rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert [row["Tax CAD"] for row in export_rows] == ["3.00", "2.00"]
    assert all("GST" not in row and "PST" not in row for row in export_rows)
    assert len(locked_calls) == 2
    current = client.get(f"/api/v1/finance/receipts/{receipt['id']}").json()
    duplicate_export = client.post(f"/api/v1/finance/receipts/{receipt['id']}/export", json={"version": current["version"], "reason": "Attempt duplicate export"})
    assert duplicate_export.status_code == 409
    assert "already exported" in duplicate_export.text
    summary = client.get(f"/api/v1/finance/projects/{project['id']}").json()
    assert summary["actual"] == 60


def test_low_confidence_and_out_of_balance_receipt_cannot_be_approved() -> None:
    project = _project("RCPT-LOW")
    _seed_vendor_and_card()
    receipt = client.post("/api/v1/finance/receipts", json=_payload(_asset(b"low-confidence"), project["id"], confidence=0.4, balanced=False)).json()
    receipt = client.post(f"/api/v1/finance/receipts/{receipt['id']}/submit", json={"version": receipt["version"], "reason": "Send uncertain extraction"}).json()
    assert receipt["is_balanced"] is False
    assert any("Low-confidence" in blocker for blocker in receipt["approval_blockers"])
    assert any("out of balance" in blocker for blocker in receipt["approval_blockers"])
    approval = client.post(f"/api/v1/finance/receipts/{receipt['id']}/approve", json={"version": receipt["version"], "reason": "Should remain blocked"})
    assert approval.status_code == 422


def test_line_totals_and_taxes_must_reconcile_before_approval() -> None:
    project = _project("RCPT-LINE")
    _seed_vendor_and_card()
    payload = _payload(_asset(b"line-mismatch"), project["id"])
    payload["line_items"][0]["line_total"] = 59
    payload["line_items"][0]["tax"] = 1
    receipt = client.post("/api/v1/finance/receipts", json=payload).json()
    receipt = client.post(
        f"/api/v1/finance/receipts/{receipt['id']}/submit",
        json={"version": receipt["version"], "reason": "Send mismatched split"},
    ).json()
    assert any("Line-item totals" in blocker for blocker in receipt["approval_blockers"])
    assert any("Line-item taxes" in blocker for blocker in receipt["approval_blockers"])
    assert any("quantity" in blocker for blocker in receipt["approval_blockers"])
    approval = client.post(
        f"/api/v1/finance/receipts/{receipt['id']}/approve",
        json={"version": receipt["version"], "reason": "Must remain blocked"},
    )
    assert approval.status_code == 422


def test_duplicate_image_and_vendor_date_amount_reference_are_flagged() -> None:
    project = _project("RCPT-DUP")
    _seed_vendor_and_card()
    first = client.post("/api/v1/finance/receipts", json=_payload(_asset(b"same-receipt"), project["id"]))
    assert first.status_code == 201
    second = client.post("/api/v1/finance/receipts", json=_payload(_asset(b"same-receipt"), project["id"]))
    assert second.status_code == 201
    assert second.json()["duplicate_of_id"] == first.json()["id"]
    assert "possible_duplicate" in second.json()["flags"]
    assert any("duplicate" in blocker.lower() for blocker in second.json()["approval_blockers"])


def test_submitter_cannot_dismiss_duplicate_or_restricted_flags() -> None:
    project = _project("RCPT-DUP-DENY")
    _seed_vendor_and_card()
    first_payload = _payload(_asset(b"duplicate-source"), project["id"])
    first = client.post("/api/v1/finance/receipts", json=first_payload)
    assert first.status_code == 201
    second_payload = _payload(_asset(b"duplicate-source"), project["id"])
    second_payload["flags"] = ["restricted_purchase"]
    second = client.post("/api/v1/finance/receipts", json=second_payload).json()

    def viewer_user(request: Request) -> AuthenticatedUser:
        principal = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email="test-admin@ironhousecontracting.com",
            display_name="Employee",
            role="viewer",
            session_version=1,
        )
        request.state.authenticated_user = principal
        return principal

    app.dependency_overrides[require_authenticated_user] = viewer_user
    attempted = client.put(
        f"/api/v1/finance/receipts/{second['id']}",
        json={
            **second_payload,
            "media_asset_ids": second["media_asset_ids"],
            "flags": [],
            "duplicate_resolution": "not_duplicate",
            "correction_reason": "Try to bypass reviewer controls",
            "version": second["version"],
        },
    )
    assert attempted.status_code == 403


def test_reviewer_can_create_vendor_but_employee_cannot_approve() -> None:
    project = _project("RCPT-VENDOR")
    payload = _payload(_asset(b"new-vendor"), project["id"])
    payload.update(vendor_name="New Civil Supply", treatment="reimbursable", card_brand=None, card_last_four=None)
    receipt = client.post("/api/v1/finance/receipts", json=payload).json()
    corrected = client.put(f"/api/v1/finance/receipts/{receipt['id']}", json={**payload, "media_asset_ids": None, "version": receipt["version"], "correction_reason": "Reviewer verified a new vendor", "create_vendor": True})
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["vendor_id"] is not None
    receipt = client.post(f"/api/v1/finance/receipts/{receipt['id']}/submit", json={"version": corrected.json()["version"], "reason": "Ready for reviewer"}).json()

    def employee_user(request: Request) -> AuthenticatedUser:
        principal = AuthenticatedUser(id=UUID("00000000-0000-0000-0000-000000000001"), email="test-admin@ironhousecontracting.com", display_name="Employee", role="viewer", session_version=1)
        request.state.authenticated_user = principal
        return principal

    app.dependency_overrides[require_authenticated_user] = employee_user
    approval = client.post(f"/api/v1/finance/receipts/{receipt['id']}/approve", json={"version": receipt["version"], "reason": "Employee cannot self approve"})
    assert approval.status_code == 403


def test_full_card_number_is_rejected_and_never_persisted() -> None:
    project = _project("RCPT-PAN")
    payload = _payload(_asset(b"pan-receipt"), project["id"])
    payload["card_brand"] = "Visa 4111111111111111"
    response = client.post("/api/v1/finance/receipts", json=payload)
    assert response.status_code == 422
    assert "last four" in response.text


def test_non_management_ai_context_excludes_other_cardholders_and_operational_records() -> None:
    _project("RCPT-CONTEXT")
    with TestingSessionLocal() as db:
        db.add_all([
            CompanyCard(brand="Visa", last_four="1111", holder_email="test-admin@ironhousecontracting.com", is_authorized=True),
            CompanyCard(brand="Visa", last_four="9999", holder_email="other@ironhousecontracting.com", is_authorized=True),
        ])
        db.commit()
        viewer = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email="test-admin@ironhousecontracting.com",
            display_name="Employee",
            role="viewer",
            session_version=1,
        )
        context = json.loads(receipt_extraction._context(db, viewer).split("\n", 1)[1])
    assert context["projects"] == []
    assert context["equipment"] == []
    assert context["authorized_cards_last_four_only"] == [{"brand": "Visa", "last_four": "1111"}]
    assert "holder_email" not in json.dumps(context["authorized_cards_last_four_only"])


def test_ai_extraction_uses_controlled_images_and_returns_unapproved_draft(monkeypatch) -> None:
    project = _project("RCPT-AI")
    _seed_vendor_and_card()
    asset_id = _asset(b"receipt-vision-input")
    raw = _payload(asset_id, project["id"])
    raw.pop("media_asset_ids")
    confidence = raw.pop("confidence")
    regions = raw.pop("source_regions")
    raw["field_evidence"] = [{"name": name, "confidence": score} for name, score in confidence.items()]
    raw["field_regions"] = [{"name": name, "source_region": region} for name, region in regions.items()]

    class ProviderResponse:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return json.dumps({"output_text": json.dumps(raw)}).encode()

    captured = {}
    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return ProviderResponse()

    monkeypatch.setattr(receipt_extraction, "get_settings", lambda: SimpleNamespace(openai_api_key="test-server-key", openai_chat_model="gpt-test-vision", openai_api_base_url="https://api.openai.test/v1"))
    monkeypatch.setattr(receipt_extraction, "urlopen", fake_urlopen)
    response = client.post("/api/v1/finance/receipts/extract", json={"media_asset_ids": [asset_id]})
    assert response.status_code == 200, response.text
    assert response.json()["model"] == "gpt-test-vision"
    assert response.json()["draft"]["vendor_name"] == "Home Hardware"
    assert response.json()["draft"]["confidence"]["total"] == 0.98
    assert "input_image" in json.dumps(captured["body"])
    assert captured["body"]["store"] is False
    assert "4111111111111111" not in json.dumps(captured["body"])
    assert client.get("/api/v1/finance/receipts").json()["total"] == 0
