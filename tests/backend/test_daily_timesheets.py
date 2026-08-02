from copy import deepcopy
from datetime import date
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.bid import Bid
from app.models.document import Document
from app.models.equipment import Equipment
from app.models.field_operations import FieldRecord
from app.models.finance import Receipt
from app.models.supplier import Supplier
from app.services.auth import AuthenticatedUser
from conftest import TestingSessionLocal


client = TestClient(app)


def _setup() -> dict:
    project_response = client.post("/api/v1/projects", json={"name": "Daily Sheet Job", "project_number": "IH-115", "status": "construction"})
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()
    other_project = client.post("/api/v1/projects", json={"name": "Other Daily Sheet Job", "project_number": "IH-115-B", "status": "construction"}).json()
    foreman = client.post("/api/v1/field-operations/employees", json={"first_name": "Fran", "last_name": "Foreman", "email": "foreman115@example.com", "portal_role": "foreman", "role": "Foreman"}).json()
    other_foreman = client.post("/api/v1/field-operations/employees", json={"first_name": "Olivia", "last_name": "Foreman", "email": "other-foreman115@example.com", "portal_role": "foreman", "role": "Foreman"}).json()
    worker = client.post("/api/v1/field-operations/employees", json={"first_name": "Casey", "last_name": "Crew", "email": "crew115@example.com", "portal_role": "employee", "role": "Pipe Layer"}).json()
    with TestingSessionLocal() as db:
        vendor = Supplier(name="Active Aggregate", category="materials", metadata_json={})
        owned = Equipment(name="EX-115 Excavator", identifier="EX-115", status="available")
        db.add_all([vendor, owned])
        db.flush()
        rental = FieldRecord(record_type="rental_equipment", project_id=UUID(project["id"]), supplier_id=vendor.id, work_date=date.today(), title="Rental plate compactor", status="active", severity="none", details={}, document_ids=[], signatures=[], alert_recipients=[])
        receipt = Receipt(submitter_id=uuid4(), submitter_email=foreman["email"], media_asset_ids=[], image_hash="1" * 64, vendor_id=vendor.id, vendor_name=vendor.name, reference="R-115", receipt_date=date.today(), confidence_json={}, source_regions_json={}, flags_json=[])
        other_receipt = Receipt(submitter_id=uuid4(), submitter_email=other_foreman["email"], media_asset_ids=[], image_hash="2" * 64, vendor_id=vendor.id, vendor_name=vendor.name, reference="R-OTHER", receipt_date=date.today(), confidence_json={}, source_regions_json={}, flags_json=[])
        document = Document(title="Daily sheet photo", category="photo", status="current", project_id=UUID(project["id"]), metadata_json={})
        other_document = Document(title="Other project photo", category="photo", status="current", project_id=UUID(other_project["id"]), metadata_json={})
        bid = Bid(project_id=UUID(project["id"]), status="approved", bid_json={"source": "estimate_workspace", "estimate": {"line_items": [{"code": "03-100", "description": "Excavation", "quantity": 100, "unit": "m3"}, {"code": "31-200", "description": "Pipe installation", "quantity": 80, "unit": "m"}]}})
        db.add_all([rental, receipt, other_receipt, document, other_document, bid])
        db.commit()
        for item in (vendor, owned, rental, receipt, other_receipt, document, other_document):
            db.refresh(item)
        return {
            "project": project,
            "foreman": foreman,
            "other_foreman": other_foreman,
            "worker": worker,
            "vendor_id": str(vendor.id),
            "equipment_id": str(owned.id),
            "rental_id": str(rental.id),
            "receipt_id": str(receipt.id),
            "other_receipt_id": str(other_receipt.id),
            "document_id": str(document.id),
            "other_document_id": str(other_document.id),
        }


def _payload(data: dict) -> dict:
    return {
        "work_date": str(date.today()), "shift": "day", "project_id": data["project"]["id"], "project_manager_id": data["foreman"]["id"], "supervisor_id": data["foreman"]["id"], "weather": "Clear, 18 C", "site_conditions": "Dry access",
        "document_ids": [data["document_id"]],
        "labour": [{"employee_id": data["worker"]["id"], "equipment_id": data["equipment_id"], "splits": [{"cost_code": "03-100", "straight_time": 5, "overtime": 0, "start_time": "07:00", "end_time": "12:00"}, {"cost_code": "31-200", "straight_time": 3, "overtime": 1, "start_time": "12:30", "end_time": "16:30"}]}],
        "equipment": [{"source": "owned", "resource_id": data["equipment_id"], "unit": "hours", "splits": [{"cost_code": "03-100", "quantity": 4}, {"cost_code": "31-200", "quantity": 4}]}, {"source": "rental", "resource_id": data["rental_id"], "vendor_id": data["vendor_id"], "unit": "hours", "splits": [{"cost_code": "31-200", "quantity": 3}]}],
        "materials": [{"description": "Pipe bedding", "vendor_id": data["vendor_id"], "cost_code": "31-200", "quantity": 12, "unit": "tonnes", "production_quantity": 24, "production_unit": "m", "receipt_id": data["receipt_id"], "document_id": data["document_id"]}],
        "narrative": {"work_completed": "Excavated and placed pipe.", "delays_issues": "None", "potential_change": True, "potential_change_details": "Unmarked crossing for office review", "safety_quality_notes": "Compaction tests passed", "general_comments": "Crew clear at 17:00"},
    }


def _principal(data: dict, key: str) -> AuthenticatedUser:
    person = data[key]
    return AuthenticatedUser(id=uuid4(), email=person["email"], display_name=f"{person['first_name']} {person['last_name']}", role="viewer", session_version=1)


def _override(principal: AuthenticatedUser):
    def dependency(request: Request) -> AuthenticatedUser:
        request.state.authenticated_user = principal
        return principal
    return dependency


def test_live_dropdown_filtering_split_totals_equipment_material_receipt_and_attachment_links() -> None:
    data = _setup()
    bootstrap = client.get("/api/v1/daily-timesheets/bootstrap")
    assert bootstrap.status_code == 200, bootstrap.text
    body = bootstrap.json()
    assert [item["code"] for item in body["project_cost_codes"][data["project"]["id"]]] == ["03-100", "31-200"]
    assert {item["id"] for item in body["equipment"]} == {data["equipment_id"]}
    assert {item["id"] for item in body["rentals"]} == {data["rental_id"]}
    created = client.post("/api/v1/daily-timesheets", json=_payload(data))
    assert created.status_code == 201, created.text
    sheet = created.json()
    assert sheet["details"]["sheet_totals"] == {"straight_time": 8.0, "overtime": 1.0, "labour_hours": 9.0}
    assert sheet["details"]["cost_code_totals"]["31-200"]["equipment_quantity"] == 7
    assert sheet["details"]["materials"][0]["receipt_id"] == data["receipt_id"]
    assert sheet["document_ids"] == [data["document_id"]]

    invalid = _payload(data)
    invalid["labour"][0]["splits"][0]["cost_code"] = "NOT-JOB"
    assert client.post("/api/v1/daily-timesheets", json=invalid).status_code == 400
    duplicate = _payload(data)
    duplicate["labour"].append(duplicate["labour"][0])
    assert client.post("/api/v1/daily-timesheets", json=duplicate).status_code == 422
    overlapping = _payload(data)
    overlapping["labour"][0]["splits"][1].update({"start_time": "11:00", "end_time": "15:00"})
    assert client.post("/api/v1/daily-timesheets", json=overlapping).status_code == 422
    wrong_project_attachment = _payload(data)
    wrong_project_attachment["document_ids"] = [data["other_document_id"]]
    assert client.post("/api/v1/daily-timesheets", json=wrong_project_attachment).status_code == 400
    wrong_material_attachment = _payload(data)
    wrong_material_attachment["materials"][0]["document_id"] = data["other_document_id"]
    assert client.post("/api/v1/daily-timesheets", json=wrong_material_attachment).status_code == 400


def test_approval_post_idempotency_and_compact_long_pdf_export() -> None:
    data = _setup()
    payload = _payload(data)
    long_text = "Detailed field progress with locations quantities constraints and follow-up actions. " * 25
    payload["narrative"].update({"work_completed": long_text, "delays_issues": long_text, "safety_quality_notes": long_text, "general_comments": long_text})
    created = client.post("/api/v1/daily-timesheets", json=payload).json()
    sheet_id = created["id"]
    submitted = client.post(f"/api/v1/daily-timesheets/{sheet_id}/submit")
    assert submitted.status_code == 200 and submitted.json()["status"] == "needs_review"
    assert submitted.json()["details"]["review_item"]["type"] == "potential_change"
    assert client.put(f"/api/v1/daily-timesheets/{sheet_id}", json=payload).status_code == 409
    approved = client.post(f"/api/v1/daily-timesheets/{sheet_id}/actions/approve", json={})
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    pdf = client.get(f"/api/v1/daily-timesheets/{sheet_id}/export.pdf")
    assert pdf.status_code == 200
    reader = PdfReader(BytesIO(pdf.content))
    assert 2 <= len(reader.pages) <= 4
    assert all((page.extract_text() or "").strip() for page in reader.pages)
    exported = client.post(f"/api/v1/daily-timesheets/{sheet_id}/export.csv")
    assert exported.status_code == 200 and "Casey Crew" in exported.text and "31-200" in exported.text
    posted = client.post(f"/api/v1/daily-timesheets/{sheet_id}/post")
    assert posted.status_code == 200 and posted.json()["details"]["posted_at"]
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/post").status_code == 409
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/revision", json={"reason": "Correct field allocation"}).status_code == 409


def test_reopen_creates_linked_revision_without_mutating_approved_source() -> None:
    data = _setup()
    sheet_id = client.post("/api/v1/daily-timesheets", json=_payload(data)).json()["id"]
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/submit").status_code == 200
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/actions/approve", json={}).status_code == 200
    with TestingSessionLocal() as db:
        source = db.get(FieldRecord, UUID(sheet_id))
        original_details = deepcopy(source.details)
        original_updated_at = source.updated_at
    reopened = client.post(f"/api/v1/daily-timesheets/{sheet_id}/actions/reopen", json={"reason": "Correct field allocation"})
    assert reopened.status_code == 200, reopened.text
    revision = reopened.json()
    assert revision["id"] != sheet_id and revision["version"] == 2 and revision["status"] == "draft"
    assert revision["details"]["previous_record_id"] == sheet_id
    with TestingSessionLocal() as db:
        source = db.get(FieldRecord, UUID(sheet_id))
        assert source.status == "approved"
        assert source.details == original_details
        assert source.updated_at == original_updated_at


def test_cross_sheet_crew_or_equipment_duplicates_are_blocked() -> None:
    data = _setup()
    first = client.post("/api/v1/daily-timesheets", json=_payload(data)).json()
    assert client.post(f"/api/v1/daily-timesheets/{first['id']}/submit").status_code == 200
    second = client.post("/api/v1/daily-timesheets", json=_payload(data)).json()
    conflict = client.post(f"/api/v1/daily-timesheets/{second['id']}/submit")
    assert conflict.status_code == 409
    assert "another active daily sheet" in conflict.text


def test_foreman_identity_receipt_and_sheet_scoping_and_office_permissions() -> None:
    data = _setup()
    original_override = app.dependency_overrides.get(require_authenticated_user)

    worker_principal = _principal(data, "worker")
    app.dependency_overrides[require_authenticated_user] = _override(worker_principal)
    assert client.get("/api/v1/daily-timesheets/bootstrap").status_code == 403

    foreman_principal = _principal(data, "foreman")
    app.dependency_overrides[require_authenticated_user] = _override(foreman_principal)
    own_payload = _payload(data)
    created = client.post("/api/v1/daily-timesheets", json=own_payload)
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]

    impersonated = _payload(data)
    impersonated["supervisor_id"] = data["other_foreman"]["id"]
    assert client.post("/api/v1/daily-timesheets", json=impersonated).status_code == 403

    other_principal = _principal(data, "other_foreman")
    app.dependency_overrides[require_authenticated_user] = _override(other_principal)
    scoped = client.get("/api/v1/daily-timesheets/bootstrap")
    assert scoped.status_code == 200
    assert sheet_id not in {item["id"] for item in scoped.json()["sheets"]}
    assert data["receipt_id"] not in {item["id"] for item in scoped.json()["receipts"]}
    assert data["other_receipt_id"] in {item["id"] for item in scoped.json()["receipts"]}
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/submit").status_code == 404
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/revision", json={"reason": "Unauthorized"}).status_code == 404

    app.dependency_overrides[require_authenticated_user] = _override(foreman_principal)
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/submit").status_code == 200
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/actions/approve", json={}).status_code == 403
    assert client.get(f"/api/v1/daily-timesheets/{sheet_id}/export.pdf").status_code == 403

    if original_override is None:
        app.dependency_overrides.pop(require_authenticated_user, None)
    else:
        app.dependency_overrides[require_authenticated_user] = original_override
