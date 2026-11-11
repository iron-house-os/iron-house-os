from datetime import date
from uuid import UUID

import pytest

from app.models.field_operations import FieldRecord
from conftest import TestingSessionLocal
from test_field_operations import _authenticate_as, _employee, _invoice_document, _project, client


def _po(project_id: str, employee_id: str | None = None, po_number: str = "PO123-IH2026001") -> dict:
    response = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "purchase_order_request",
            "project_id": project_id,
            "employee_id": employee_id,
            "work_date": str(date.today()),
            "title": "PO regression",
            "details": {"po_number": po_number, "purpose": "Pipe"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _invoice(document_id: str) -> dict:
    return {
        "document_id": document_id,
        "invoice_number": "INV-SECURITY",
        "vendor_name": "Supplier",
        "invoice_date": str(date.today()),
        "subtotal": 100,
        "tax": 5,
        "total": 105,
    }


@pytest.mark.parametrize("role", ["viewer", "admin"])
def test_po_creation_cannot_forge_invoice_approval(role: str) -> None:
    employee = _employee()
    project = _project()
    _authenticate_as(role, employee["email"] if role == "viewer" else None)
    response = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "purchase_order_request",
            "project_id": project["id"],
            "work_date": str(date.today()),
            "title": "Forged approval",
            "status": "approved",
            "signatures": [{"employee_name": "Invented approver"}],
            "details": {
                "purpose": "Pipe",
                "invoice": {"invoice_number": "FAKE"},
                "invoice_status": "approved",
                "invoice_decision": {"decision": "approved", "by": "Management"},
                "invoice_audit_history": [{"action": "approved"}],
            },
        },
    )
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["status"] == "pending_approval"
    assert record["signatures"] == []
    assert record["details"] == {"purpose": "Pipe"}
    with TestingSessionLocal() as db:
        stored = db.get(FieldRecord, UUID(record["id"]))
        assert stored is not None
        assert stored.details == {"purpose": "Pipe"}
        assert stored.signatures == []
    _authenticate_as("admin")
    decision = client.post(
        f"/api/v1/field-operations/records/{record['id']}/invoice-decision",
        json={"decision": "approved"},
    )
    assert decision.status_code == 409


def test_invoice_attachment_denies_unassigned_project_before_document_lookup() -> None:
    employee = _employee()
    project = client.post(
        "/api/v1/projects", json={"name": "Restricted job", "status": "awarded"}
    ).json()
    assert client.post(f"/api/v1/projects/{project['id']}/safety-launch").status_code == 201
    po = _po(project["id"], employee["id"])
    document_id = _invoice_document(project["id"])
    _authenticate_as("viewer", employee["email"])

    for candidate_id in (document_id, "00000000-0000-0000-0000-000000000099"):
        denied = client.post(
            f"/api/v1/field-operations/records/{po['id']}/invoice",
            json=_invoice(candidate_id),
        )
        assert denied.status_code == 403, denied.text

    with TestingSessionLocal() as db:
        stored = db.get(FieldRecord, UUID(po["id"]))
        assert stored is not None
        assert stored.details == po["details"]
        assert stored.document_ids == []


def test_invoice_attachment_denies_other_worker_but_allows_own_po() -> None:
    employee = _employee()
    project = _project()
    other_po = _po(project["id"])
    document_id = _invoice_document(project["id"])
    _authenticate_as("viewer", employee["email"])
    denied = client.post(
        f"/api/v1/field-operations/records/{other_po['id']}/invoice",
        json=_invoice(document_id),
    )
    assert denied.status_code == 403, denied.text
    own_po = _po(project["id"])
    attached = client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice",
        json=_invoice(document_id),
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["details"]["invoice_status"] == "pending_approval"
    assert attached.json()["details"]["invoice_audit_history"][0]["email"] == employee["email"]
    denied_decision = client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice-decision",
        json={"decision": "approved"},
    )
    assert denied_decision.status_code == 403
    _authenticate_as("admin")
    approved = client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice-decision",
        json={"decision": "approved"},
    )
    assert approved.status_code == 200, approved.text


def test_replacement_invoice_does_not_retain_previous_approval_decision() -> None:
    project = _project()
    po = _po(project["id"])
    endpoint = f"/api/v1/field-operations/records/{po['id']}"
    attached = client.post(endpoint + "/invoice", json=_invoice(_invoice_document(project["id"])))
    assert attached.status_code == 200, attached.text
    approved = client.post(endpoint + "/invoice-decision", json={"decision": "approved"})
    assert approved.status_code == 200, approved.text
    replacement = client.post(
        endpoint + "/invoice", json=_invoice(_invoice_document(project["id"], "replacement.pdf"))
    )
    assert replacement.status_code == 200, replacement.text
    details = replacement.json()["details"]
    assert details["invoice_status"] == "pending_approval"
    assert "invoice_decision" not in details
    assert [event["action"] for event in details["invoice_audit_history"]] == [
        "attached", "approved", "attached"
    ]


def test_duplicate_warning_does_not_disclose_unassigned_project_po() -> None:
    employee = _employee()
    restricted = client.post(
        "/api/v1/projects", json={"name": "Private job", "status": "awarded"}
    ).json()
    assert client.post(f"/api/v1/projects/{restricted['id']}/safety-launch").status_code == 201
    hidden_po = _po(restricted["id"])
    attached = client.post(
        f"/api/v1/field-operations/records/{hidden_po['id']}/invoice",
        json=_invoice(_invoice_document(restricted["id"])),
    )
    assert attached.status_code == 200, attached.text
    project = _project()
    document_id = _invoice_document(project["id"])
    _authenticate_as("viewer", employee["email"])
    own_po = _po(project["id"])
    attached = client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice",
        json=_invoice(document_id),
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["details"]["invoice"]["duplicate_po_numbers"] == []


def _bootstrap_po(record_id: str) -> dict:
    response = client.get("/api/v1/field-operations/bootstrap")
    assert response.status_code == 200, response.text
    return next(record for record in response.json()["records"] if record["id"] == record_id)


@pytest.mark.parametrize("uploader", ["viewer", "admin"])
def test_duplicate_visibility_is_per_reader_and_preserves_full_internal_matches(uploader: str) -> None:
    employee = _employee()
    restricted = client.post(
        "/api/v1/projects", json={"name": "Private duplicate job", "status": "awarded"}
    ).json()
    assert client.post(f"/api/v1/projects/{restricted['id']}/safety-launch").status_code == 201
    hidden_po = _po(restricted["id"], po_number="SECRET-PO")
    assert client.post(
        f"/api/v1/field-operations/records/{hidden_po['id']}/invoice",
        json=_invoice(_invoice_document(restricted["id"])),
    ).status_code == 200
    project = _project()
    own_po = _po(project["id"], employee["id"], po_number="OWN-PO")
    document_id = _invoice_document(project["id"])
    _authenticate_as(uploader, employee["email"] if uploader == "viewer" else None)
    attached = client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice",
        json=_invoice(document_id),
    )
    assert attached.status_code == 200, attached.text
    expected = ["SECRET-PO"] if uploader == "admin" else []
    assert attached.json()["details"]["invoice"]["duplicate_po_numbers"] == expected
    with TestingSessionLocal() as db:
        stored = db.get(FieldRecord, UUID(own_po["id"]))
        assert stored.details["invoice"]["duplicate_po_numbers"] == ["SECRET-PO"]

    _authenticate_as("viewer", employee["email"])
    assert _bootstrap_po(own_po["id"])["details"]["invoice"]["duplicate_po_numbers"] == []
    signed = client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/sign",
        json={"employee_id": employee["id"], "employee_name": "Crew Member"},
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["details"]["invoice"]["duplicate_po_numbers"] == []

    _authenticate_as("admin")
    assert _bootstrap_po(own_po["id"])["details"]["invoice"]["duplicate_po_numbers"] == ["SECRET-PO"]
    decision = client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice-decision",
        json={"decision": "approved"},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["details"]["invoice"]["duplicate_po_numbers"] == ["SECRET-PO"]


def test_legacy_duplicate_lists_are_recomputed_and_nested_warnings_are_redacted_without_mutation() -> None:
    employee = _employee()
    restricted = client.post(
        "/api/v1/projects", json={"name": "Legacy private job", "status": "awarded"}
    ).json()
    assert client.post(f"/api/v1/projects/{restricted['id']}/safety-launch").status_code == 201
    hidden_po = _po(restricted["id"], po_number="LEGACY-SECRET")
    assert client.post(
        f"/api/v1/field-operations/records/{hidden_po['id']}/invoice",
        json=_invoice(_invoice_document(restricted["id"])),
    ).status_code == 200
    project = _project()
    own_po = _po(project["id"], employee["id"], po_number="LEGACY-OWN")
    assert client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice",
        json=_invoice(_invoice_document(project["id"])),
    ).status_code == 200
    with TestingSessionLocal() as db:
        stored = db.get(FieldRecord, UUID(own_po["id"]))
        details = dict(stored.details)
        details["invoice"] = {**details["invoice"], "duplicate_po_numbers": []}
        details["invoice_audit_history"] = [
            {"action": "legacy_snapshot", "invoice": {"duplicate_po_numbers": ["LEGACY-SECRET"]}}
        ]
        stored.details = details
        db.commit()

    _authenticate_as("viewer", employee["email"])
    serialized = _bootstrap_po(own_po["id"])
    assert serialized["details"]["invoice"]["duplicate_po_numbers"] == []
    assert serialized["details"]["invoice_audit_history"][0]["invoice"]["duplicate_po_numbers"] == []
    with TestingSessionLocal() as db:
        stored = db.get(FieldRecord, UUID(own_po["id"]))
        assert stored.details["invoice"]["duplicate_po_numbers"] == []
        assert stored.details["invoice_audit_history"][0]["invoice"]["duplicate_po_numbers"] == ["LEGACY-SECRET"]
    _authenticate_as("admin")
    assert _bootstrap_po(own_po["id"])["details"]["invoice"]["duplicate_po_numbers"] == ["LEGACY-SECRET"]


def test_duplicate_warnings_follow_current_project_access_and_include_later_uploads() -> None:
    employee = _employee()
    project = _project()
    own_po = _po(project["id"], employee["id"], po_number="FIRST-OWN")
    assert client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice",
        json=_invoice(_invoice_document(project["id"])),
    ).status_code == 200
    later_project = client.post(
        "/api/v1/projects", json={"name": "Later controlled job", "status": "awarded"}
    ).json()
    later_po = _po(later_project["id"], employee["id"], po_number="LATER-OWN")
    assert client.post(
        f"/api/v1/field-operations/records/{later_po['id']}/invoice",
        json=_invoice(_invoice_document(later_project["id"])),
    ).status_code == 200

    _authenticate_as("viewer", employee["email"])
    assert _bootstrap_po(own_po["id"])["details"]["invoice"]["duplicate_po_numbers"] == ["LATER-OWN"]
    _authenticate_as("admin")
    assert client.post(f"/api/v1/projects/{later_project['id']}/safety-launch").status_code == 201
    _authenticate_as("viewer", employee["email"])
    assert _bootstrap_po(own_po["id"])["details"]["invoice"]["duplicate_po_numbers"] == []
    _authenticate_as("admin")
    assert _bootstrap_po(own_po["id"])["details"]["invoice"]["duplicate_po_numbers"] == ["LATER-OWN"]


def test_legacy_warning_collision_does_not_authorize_a_restricted_reference() -> None:
    employee = _employee()
    restricted = client.post(
        "/api/v1/projects", json={"name": "Restricted collision job", "status": "awarded"}
    ).json()
    assert client.post(f"/api/v1/projects/{restricted['id']}/safety-launch").status_code == 201
    hidden_po = _po(restricted["id"], po_number="COLLIDING-PO")
    assert client.post(
        f"/api/v1/field-operations/records/{hidden_po['id']}/invoice",
        json=_invoice(_invoice_document(restricted["id"])),
    ).status_code == 200

    project = _project()
    # A caller can supply the same PO number on a readable record, without
    # actually holding the historical invoice association that number denotes.
    visible_collision = _po(project["id"], employee["id"], po_number="COLLIDING-PO")
    own_po = _po(project["id"], employee["id"], po_number="OWN-WITH-SNAPSHOT")
    assert client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/invoice",
        json=_invoice(_invoice_document(project["id"])),
    ).status_code == 200
    snapshot = [{"action": "snapshot", "invoice": {"duplicate_po_numbers": ["COLLIDING-PO"]}}]
    with TestingSessionLocal() as db:
        stored = db.get(FieldRecord, UUID(own_po["id"]))
        stored.details = {**stored.details, "invoice_audit_history": snapshot}
        db.commit()

    _authenticate_as("viewer", employee["email"])
    assert "invoice" not in _bootstrap_po(visible_collision["id"])["details"]
    serialized = _bootstrap_po(own_po["id"])
    assert serialized["details"]["invoice"]["duplicate_po_numbers"] == []
    assert serialized["details"]["invoice_audit_history"][0]["invoice"]["duplicate_po_numbers"] == []
    signed = client.post(
        f"/api/v1/field-operations/records/{own_po['id']}/sign",
        json={"employee_id": employee["id"], "employee_name": "Crew Member"},
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["details"]["invoice_audit_history"][0]["invoice"]["duplicate_po_numbers"] == []
    with TestingSessionLocal() as db:
        stored = db.get(FieldRecord, UUID(own_po["id"]))
        assert stored.details["invoice_audit_history"] == snapshot
    _authenticate_as("admin")
    serialized = _bootstrap_po(own_po["id"])
    assert serialized["details"]["invoice"]["duplicate_po_numbers"] == ["COLLIDING-PO"]
    assert serialized["details"]["invoice_audit_history"] == snapshot
