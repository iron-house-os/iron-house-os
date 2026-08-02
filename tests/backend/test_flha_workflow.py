from datetime import date
from io import BytesIO
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser


client = TestClient(app)


def create_employee(name: str, email: str, portal_role: str = "employee") -> dict:
    first, last = name.split(" ", 1)
    response = client.post("/api/v1/field-operations/employees", json={
        "first_name": first, "last_name": last, "email": email, "portal_role": portal_role,
    })
    assert response.status_code == 201
    return response.json()


def create_project() -> dict:
    response = client.post("/api/v1/projects", json={"name": "Mobile FLHA Test", "project_number": "FLHA-113"})
    assert response.status_code == 201
    return response.json()


def complete_details(crew: list[dict], *, critical: bool = False) -> dict:
    return {
        "project_name": "Mobile FLHA Test",
        "site_location": "North excavation",
        "assessment_datetime": "2026-08-02T07:00",
        "supervisor": {"id": crew[0]["id"], "name": f"{crew[0]['first_name']} {crew[0]['last_name']}"},
        "first_aid_attendant": {"id": crew[0]["id"], "name": f"{crew[0]['first_name']} {crew[0]['last_name']}"},
        "crew": [{"id": item["id"], "name": f"{item['first_name']} {item['last_name']}"} for item in crew],
        "weather": "Clear, 18 C",
        "screening": {
            "first_aid_equipment": "yes", "overhead_hazards": "na", "underground_utilities_and_locates": "yes",
            "mobile_equipment": "yes", "confined_space": "na", "excavation_sloping_shoring_and_access": "yes",
            "additional_ppe": "no", "traffic_control": "na", "subcontractors": "no", "basic_ppe_review": "yes",
        },
        "hazards": [{
            "task": "Excavate", "hazard": "Utility contact", "control": "Verify locates and daylight crossings",
            "responsible_person": "Test Foreperson", "control_level": "engineering", "risk": "critical" if critical else "high",
            "accepted_control": True, "evidence_required": critical, "evidence": "Locate package 113" if critical else "",
        }],
        "emergency": {
            "response_plan": "Call 911 and notify supervision", "muster_point": "Site trailer",
            "first_aid_location": "Foreperson truck", "communication": "Radio channel 2",
            "stop_work_triggers": "Conditions change or a control fails",
        },
    }


def create_flha(project: dict, crew: list[dict], details: dict | None = None) -> dict:
    response = client.post("/api/v1/field-operations/records", json={
        "record_type": "daily_hazard_assessment", "project_id": project["id"], "work_date": str(date.today()),
        "title": "Excavation FLHA", "details": details or complete_details(crew),
    })
    assert response.status_code == 201
    return response.json()


def test_flha_create_edit_sign_release_audit_and_immutability() -> None:
    worker = create_employee("Crew Worker", "crew.worker@example.com")
    project = create_project()
    initial = complete_details([worker])
    initial.update({
        "schema_version": 99,
        "version": 99,
        "root_record_id": "forged-root",
        "audit_history": [{"action": "forged", "by": "attacker@example.com"}],
        "supervisor_release": {"released_by": "attacker@example.com"},
        "release_blockers": [],
    })
    record = create_flha(project, [worker], initial)
    assert record["status"] == "draft"
    assert record["details"]["schema_version"] == 1
    assert record["details"]["version"] == 1
    assert record["details"]["root_record_id"] is None
    assert [event["action"] for event in record["details"]["audit_history"]] == ["created"]
    assert "supervisor_release" not in record["details"]
    assert record["details"]["release_blockers"] == []

    changed = complete_details([worker])
    changed["weather"] = "Cloud increasing, 16 C"
    changed.update({
        "version": 88,
        "audit_history": [{"action": "forged-edit"}],
        "supervisor_release": {"released_by": "attacker@example.com"},
    })
    edited = client.patch(f"/api/v1/field-operations/records/{record['id']}/flha", json={
        "project_id": project["id"], "work_date": str(date.today()), "title": record["title"], "details": changed,
    })
    assert edited.status_code == 200
    assert edited.json()["details"]["version"] == 1
    assert [event["action"] for event in edited.json()["details"]["audit_history"]] == ["created", "edited"]
    assert "supervisor_release" not in edited.json()["details"]

    signed = client.post(f"/api/v1/field-operations/records/{record['id']}/sign", json={
        "employee_id": worker["id"], "employee_name": "Forged Worker Name",
        "acknowledgement": "I reviewed the hazards and controls with the foreperson.",
        "supervised_shared_device": True,
        "supervisor_confirmation": "I observed the worker review and personally acknowledge this FLHA.",
    })
    assert signed.status_code == 200
    assert signed.json()["signatures"][0]["employee_name"] == "Crew Worker"
    assert signed.json()["signatures"][0]["signing_method"] == "supervised_shared_device"

    frozen = client.patch(f"/api/v1/field-operations/records/{record['id']}/flha", json={
        "project_id": project["id"], "work_date": str(date.today()), "title": "Changed", "details": changed,
    })
    assert frozen.status_code == 409

    released = client.post(f"/api/v1/field-operations/records/{record['id']}/flha/release", json={
        "verification": "I inspected the work area and verified the listed crew and controls in place.",
    })
    assert released.status_code == 200
    assert released.json()["status"] == "released"
    audit = client.get(f"/api/v1/field-operations/records/{record['id']}/flha/audit")
    assert audit.status_code == 200
    assert [event["action"] for event in audit.json()["events"]][-2:] == ["worker_acknowledged", "supervisor_released"]


def test_uncontrolled_critical_hazard_blocks_acknowledgement_and_release() -> None:
    worker = create_employee("Critical Worker", "critical.worker@example.com")
    project = create_project()
    details = complete_details([worker], critical=True)
    details["hazards"][0].update({"accepted_control": False, "responsible_person": "", "evidence": ""})
    record = create_flha(project, [worker], details)
    assert record["status"] == "blocked"
    assert len(record["details"]["release_blockers"]) >= 3

    sign = client.post(f"/api/v1/field-operations/records/{record['id']}/sign", json={
        "employee_id": worker["id"], "employee_name": "Critical Worker", "acknowledgement": "I reviewed this blocked assessment.",
        "supervised_shared_device": True, "supervisor_confirmation": "Supervised review.",
    })
    assert sign.status_code == 409
    release = client.post(f"/api/v1/field-operations/records/{record['id']}/flha/release", json={"verification": "I checked the work location and crew."})
    assert release.status_code == 409


def test_reassessment_creates_new_version_and_requires_new_acknowledgement() -> None:
    worker = create_employee("Version Worker", "version.worker@example.com")
    project = create_project()
    original = create_flha(project, [worker])
    signed = client.post(f"/api/v1/field-operations/records/{original['id']}/sign", json={
        "employee_id": worker["id"], "employee_name": "Version Worker", "acknowledgement": "I reviewed the original FLHA controls.",
        "supervised_shared_device": True, "supervisor_confirmation": "Supervised review.",
    })
    assert signed.status_code == 200
    revised_details = complete_details([worker])
    revised_details["weather"] = "Heavy rain"
    revised = client.post(f"/api/v1/field-operations/records/{original['id']}/flha/reassess", json={
        "project_id": project["id"], "work_date": str(date.today()), "title": "Rain re-assessment",
        "details": revised_details, "reason": "Weather materially changed", "changed_conditions": ["weather"],
    })
    assert revised.status_code == 201
    assert revised.json()["id"] != original["id"]
    assert revised.json()["details"]["version"] == 2
    assert revised.json()["details"]["previous_record_id"] == original["id"]
    assert revised.json()["signatures"] == []
    stored_original = next(item for item in client.get("/api/v1/field-operations/bootstrap").json()["records"] if item["id"] == original["id"])
    assert len(stored_original["signatures"]) == 1


def test_worker_permissions_visibility_and_own_device_signature() -> None:
    worker = create_employee("Own Device", "own.device@example.com")
    outsider = create_employee("Other Worker", "other.worker@example.com")
    project = create_project()
    record = create_flha(project, [worker])

    def worker_user(request: Request) -> AuthenticatedUser:
        principal = AuthenticatedUser(id=UUID("00000000-0000-0000-0000-000000000101"), email=worker["email"], display_name="Own Device", role="viewer", session_version=1)
        request.state.authenticated_user = principal
        return principal

    app.dependency_overrides[require_authenticated_user] = worker_user
    visible = client.get("/api/v1/field-operations/bootstrap")
    assert visible.status_code == 200
    assert [item["id"] for item in visible.json()["records"]] == [record["id"]]
    forbidden_create = client.post("/api/v1/field-operations/records", json={
        "record_type": "daily_hazard_assessment", "project_id": project["id"], "work_date": str(date.today()),
        "title": "Unauthorized", "details": complete_details([worker]),
    })
    assert forbidden_create.status_code == 403
    own_sign = client.post(f"/api/v1/field-operations/records/{record['id']}/sign", json={
        "employee_id": worker["id"], "employee_name": "Own Device", "acknowledgement": "I reviewed and understand this FLHA version.",
    })
    assert own_sign.status_code == 200
    assert own_sign.json()["signatures"][0]["signing_method"] == "own_device"
    other_sign = client.post(f"/api/v1/field-operations/records/{record['id']}/sign", json={
        "employee_id": outsider["id"], "employee_name": "Other Worker", "acknowledgement": "Attempted unauthorized signature.",
    })
    assert other_sign.status_code == 403


def test_pdf_is_legible_compact_and_has_no_blank_overflow_pages() -> None:
    crew = [create_employee(f"Worker {index}", f"worker{index}@example.com") for index in range(1, 19)]
    project = create_project()
    details = complete_details(crew)
    details["hazards"] = [{**details["hazards"][0], "task": f"Task {index}", "hazard": f"Hazard {index}"} for index in range(1, 9)]
    record = create_flha(project, crew, details)
    pdf = client.get(f"/api/v1/field-operations/records/{record['id']}/flha.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    reader = PdfReader(BytesIO(pdf.content))
    assert 1 < len(reader.pages) < 6
    page_text = [page.extract_text() for page in reader.pages]
    assert all(len(text.strip()) > 80 for text in page_text)
    assert "FIELD LEVEL HAZARD ASSESSMENT" in page_text[0]
    combined = "\n".join(page_text)
    assert "Worker 1" in combined and "Worker 18" in combined
