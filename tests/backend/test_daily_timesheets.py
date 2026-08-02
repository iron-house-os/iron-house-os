from datetime import date
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.bid import Bid
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
    foreman = client.post("/api/v1/field-operations/employees", json={"first_name": "Fran", "last_name": "Foreman", "email": "foreman115@example.com", "portal_role": "foreman", "role": "Foreman"}).json()
    worker = client.post("/api/v1/field-operations/employees", json={"first_name": "Casey", "last_name": "Crew", "email": "crew115@example.com", "portal_role": "employee", "role": "Pipe Layer"}).json()
    with TestingSessionLocal() as db:
        vendor = Supplier(name="Active Aggregate", category="materials", metadata_json={})
        owned = Equipment(name="EX-115 Excavator", identifier="EX-115", status="available")
        db.add_all([vendor, owned]); db.flush()
        rental = FieldRecord(record_type="rental_equipment", project_id=UUID(project["id"]), supplier_id=vendor.id, work_date=date.today(), title="Rental plate compactor", status="active", severity="none", details={}, document_ids=[], signatures=[], alert_recipients=[])
        receipt = Receipt(submitter_id=uuid4(), submitter_email="foreman115@example.com", media_asset_ids=[], image_hash="1" * 64, vendor_id=vendor.id, vendor_name=vendor.name, reference="R-115", receipt_date=date.today(), confidence_json={}, source_regions_json={}, flags_json=[])
        bid = Bid(project_id=UUID(project["id"]), status="approved", bid_json={"source": "estimate_workspace", "estimate": {"line_items": [{"code": "03-100", "description": "Excavation", "quantity": 100, "unit": "m3"}, {"code": "31-200", "description": "Pipe installation", "quantity": 80, "unit": "m"}]}})
        db.add_all([rental, receipt, bid]); db.commit()
        for item in (vendor, owned, rental, receipt): db.refresh(item)
        return {"project": project, "foreman": foreman, "worker": worker, "vendor_id": str(vendor.id), "equipment_id": str(owned.id), "rental_id": str(rental.id), "receipt_id": str(receipt.id)}


def _payload(data: dict) -> dict:
    return {
        "work_date": str(date.today()), "shift": "day", "project_id": data["project"]["id"], "project_manager_id": data["foreman"]["id"], "supervisor_id": data["foreman"]["id"], "weather": "Clear, 18 C", "site_conditions": "Dry access",
        "labour": [{"employee_id": data["worker"]["id"], "equipment_id": data["equipment_id"], "splits": [{"cost_code": "03-100", "straight_time": 5, "overtime": 0, "start_time": "07:00", "end_time": "12:00"}, {"cost_code": "31-200", "straight_time": 3, "overtime": 1, "start_time": "12:30", "end_time": "16:30"}]}],
        "equipment": [{"source": "owned", "resource_id": data["equipment_id"], "unit": "hours", "splits": [{"cost_code": "03-100", "quantity": 4}, {"cost_code": "31-200", "quantity": 4}]}, {"source": "rental", "resource_id": data["rental_id"], "vendor_id": data["vendor_id"], "unit": "hours", "splits": [{"cost_code": "31-200", "quantity": 3}]}],
        "materials": [{"description": "Pipe bedding", "vendor_id": data["vendor_id"], "cost_code": "31-200", "quantity": 12, "unit": "tonnes", "production_quantity": 24, "production_unit": "m", "receipt_id": data["receipt_id"]}],
        "narrative": {"work_completed": "Excavated and placed pipe.", "delays_issues": "None", "potential_change": True, "potential_change_details": "Unmarked crossing for office review", "safety_quality_notes": "Compaction tests passed", "general_comments": "Crew clear at 17:00"},
    }


def test_live_dropdown_filtering_split_totals_equipment_material_and_receipt_links() -> None:
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

    invalid = _payload(data); invalid["labour"][0]["splits"][0]["cost_code"] = "NOT-JOB"
    assert client.post("/api/v1/daily-timesheets", json=invalid).status_code == 400
    duplicate = _payload(data); duplicate["labour"].append(duplicate["labour"][0])
    assert client.post("/api/v1/daily-timesheets", json=duplicate).status_code == 422
    overlapping = _payload(data); overlapping["labour"][0]["splits"][1].update({"start_time": "11:00", "end_time": "15:00"})
    assert client.post("/api/v1/daily-timesheets", json=overlapping).status_code == 422


def test_approval_immutability_revision_post_and_compact_exports() -> None:
    data = _setup(); created = client.post("/api/v1/daily-timesheets", json=_payload(data)).json(); sheet_id = created["id"]
    submitted = client.post(f"/api/v1/daily-timesheets/{sheet_id}/submit")
    assert submitted.status_code == 200 and submitted.json()["status"] == "needs_review"
    assert submitted.json()["details"]["review_item"]["type"] == "potential_change"
    assert client.put(f"/api/v1/daily-timesheets/{sheet_id}", json=_payload(data)).status_code == 409
    approved = client.post(f"/api/v1/daily-timesheets/{sheet_id}/actions/approve", json={})
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    pdf = client.get(f"/api/v1/daily-timesheets/{sheet_id}/export.pdf")
    assert pdf.status_code == 200
    reader = PdfReader(BytesIO(pdf.content))
    assert 1 <= len(reader.pages) <= 3
    assert all((page.extract_text() or "").strip() for page in reader.pages)
    exported = client.post(f"/api/v1/daily-timesheets/{sheet_id}/export.csv")
    assert exported.status_code == 200 and "Casey Crew" in exported.text and "31-200" in exported.text
    posted = client.post(f"/api/v1/daily-timesheets/{sheet_id}/post")
    assert posted.status_code == 200 and posted.json()["details"]["posted_at"]
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/post").status_code == 409
    revision = client.post(f"/api/v1/daily-timesheets/{sheet_id}/revision", json={"reason": "Correct field allocation"})
    assert revision.status_code == 201 and revision.json()["version"] == 2 and revision.json()["status"] == "draft"
    assert revision.json()["details"]["previous_record_id"] == sheet_id


def test_only_foremen_submit_and_only_office_roles_approve_export_or_reopen() -> None:
    data = _setup()
    sheet_id = client.post("/api/v1/daily-timesheets", json=_payload(data)).json()["id"]

    def viewer(request: Request) -> AuthenticatedUser:
        principal = AuthenticatedUser(id=uuid4(), email=data["worker"]["email"], display_name="Casey Crew", role="viewer", session_version=1)
        request.state.authenticated_user = principal
        return principal

    app.dependency_overrides[require_authenticated_user] = viewer
    assert client.get("/api/v1/daily-timesheets/bootstrap").status_code == 403
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/submit").status_code == 403

    def foreman(request: Request) -> AuthenticatedUser:
        principal = AuthenticatedUser(id=uuid4(), email=data["foreman"]["email"], display_name="Fran Foreman", role="viewer", session_version=1)
        request.state.authenticated_user = principal
        return principal

    app.dependency_overrides[require_authenticated_user] = foreman
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/submit").status_code == 200
    assert client.post(f"/api/v1/daily-timesheets/{sheet_id}/actions/approve", json={}).status_code == 403
    assert client.get(f"/api/v1/daily-timesheets/{sheet_id}/export.pdf").status_code == 403
