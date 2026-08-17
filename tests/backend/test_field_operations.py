from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from fastapi import Request
from uuid import UUID

from app.main import app
from app.core.errors import AppError
from app.schemas.field_operations import SafetyRecordUpdate
from app.services import field_operations
from app.api.dependencies.auth import require_authenticated_user
from app.services.auth import AuthenticatedUser


client = TestClient(app)


def _authenticate_as(role: str, email: str | None = None) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000070"),
            email=email or f"{role}@ironhousecontracting.com",
            display_name=f"Test {role.replace('_', ' ').title()}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _employee() -> dict:
    response = client.post(
        "/api/v1/field-operations/employees",
        json={
            "first_name": "Crew",
            "last_name": "Member",
            "email": "crew.member@ironhousecontracting.com",
            "portal_role": "operator",
            "phone": "604-555-0100",
            "emergency_contact_name": "Emergency Contact",
            "emergency_contact_phone": "604-555-0101",
        },
    )
    assert response.status_code == 201
    return response.json()


def _project() -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": "Field Operations Test", "project_number": "FIELD-OPS-001"},
    )
    assert response.status_code == 201
    return response.json()


def test_field_operations_links_time_to_employee_project_and_cost_code() -> None:
    employee = _employee()
    project = _project()

    response = client.post(
        "/api/v1/field-operations/time-entries",
        json={
            "employee_id": employee["id"],
            "project_id": project["id"],
            "cost_code": "02-200",
            "work_date": str(date.today()),
            "regular_hours": 8,
            "overtime_hours": 1.5,
            "entry_type": "operator",
        },
    )

    assert response.status_code == 201
    assert response.json()["regular_hours"] == 8
    bootstrap = client.get("/api/v1/field-operations/bootstrap")
    assert bootstrap.status_code == 200
    assert bootstrap.json()["time_entries"][0]["cost_code"] == "02-200"


def test_vehicle_log_updates_odometer_and_service_alert() -> None:
    vehicle = client.post(
        "/api/v1/field-operations/vehicles",
        json={
            "unit_number": "099",
            "name": "Test GMC 3500",
            "assigned_driver_name": "Test Driver",
            "make": "GMC",
            "model": "3500",
            "current_km": 9000,
            "next_service_km": 10000,
        },
    )
    assert vehicle.status_code == 201
    vehicle_id = vehicle.json()["id"]

    response = client.post(
        "/api/v1/field-operations/vehicle-logs",
        json={
            "vehicle_id": vehicle_id,
            "log_type": "fuel",
            "entry_date": str(date.today()),
            "odometer_km": 10025,
            "litres": 75,
            "amount": 145.50,
            "vendor": "Fuel Vendor",
        },
    )

    assert response.status_code == 201
    bootstrap = client.get("/api/v1/field-operations/bootstrap").json()
    stored = next(item for item in bootstrap["vehicles"] if item["id"] == vehicle_id)
    assert stored["current_km"] == 10025
    assert stored["service_status"] == "overdue"
    assert any(alert["type"] == "vehicle_service" for alert in bootstrap["alerts"])


def test_flagged_inspection_alerts_management_and_accepts_signature() -> None:
    employee = _employee()
    project = _project()
    record = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "equipment_inspection",
            "project_id": project["id"],
            "employee_id": employee["id"],
            "work_date": str(date.today()),
            "title": "Hydraulic leak at boom",
            "severity": "high",
            "details": {"component": "boom", "machine_hours": 2810},
        },
    )
    assert record.status_code == 201
    assert record.json()["alert_recipients"] == ["Jeremie Peters", "Mac Warren"]

    signed = client.post(
        f"/api/v1/field-operations/records/{record.json()['id']}/sign",
        json={
            "employee_id": employee["id"],
            "employee_name": "Crew Member",
            "acknowledgement": "I acknowledge this inspection and the required controls.",
        },
    )
    assert signed.status_code == 200
    assert signed.json()["signatures"][0]["employee_name"] == "Crew Member"


def test_safety_control_records_require_evidence_for_release_and_keep_history() -> None:
    project = _project()
    created = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "safety_permit",
            "project_id": project["id"],
            "work_date": str(date.today()),
            "title": "Ground disturbance permit",
            "severity": "high",
            "details": {"task": "Excavate water service", "supervisor": "Safety Lead"},
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "blocked"

    missing_evidence = client.patch(
        f"/api/v1/field-operations/records/{created.json()['id']}/safety-status",
        json={"status": "ready"},
    )
    assert missing_evidence.status_code == 422

    released = client.patch(
        f"/api/v1/field-operations/records/{created.json()['id']}/safety-status",
        json={"status": "ready", "evidence": "Utility locates and daylighting were verified at the work face."},
    )
    assert released.status_code == 200
    assert released.json()["status"] == "ready"
    assert released.json()["details"]["status_history"][-1]["from"] == "blocked"


def test_safety_status_endpoint_rejects_non_safety_records() -> None:
    created = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "journal",
            "work_date": str(date.today()),
            "title": "Daily note",
        },
    )
    response = client.patch(
        f"/api/v1/field-operations/records/{created.json()['id']}/safety-status",
        json={"status": "closed", "evidence": "Not applicable."},
    )
    assert response.status_code == 400


def test_incident_records_are_durable_alert_management_and_require_ordered_review() -> None:
    employee = _employee()
    created = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "incident",
            "employee_id": employee["id"],
            "work_date": str(date.today()),
            "title": "Excavator swing near miss",
            "severity": "high",
            "details": {
                "occurrence_kind": "near_miss",
                "occurred_at": f"{date.today()}T09:30",
                "location": "Field Operations Test",
                "description": "A worker entered the swing-radius boundary.",
                "immediate_controls": "Work stopped and the exclusion zone was re-established.",
            },
        },
    )
    assert created.status_code == 201
    record = created.json()
    assert record["status"] == "reported"
    assert record["alert_recipients"] == ["Jeremie Peters", "Mac Warren"]
    assert record["details"]["reported_by"] == "Test Administrator"

    missing_review_evidence = client.patch(
        f"/api/v1/field-operations/records/{record['id']}/safety-status",
        json={"status": "under_review"},
    )
    assert missing_review_evidence.status_code == 422

    skipped_review = client.patch(
        f"/api/v1/field-operations/records/{record['id']}/safety-status",
        json={"status": "closed", "evidence": "Management reviewed the occurrence."},
    )
    assert skipped_review.status_code == 409

    under_review = client.patch(
        f"/api/v1/field-operations/records/{record['id']}/safety-status",
        json={"status": "under_review", "evidence": "Assigned to the operations manager."},
    )
    assert under_review.status_code == 200
    assert under_review.json()["status"] == "under_review"

    closed = client.patch(
        f"/api/v1/field-operations/records/{record['id']}/safety-status",
        json={"status": "closed", "evidence": "Boundary controls were verified with the crew."},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert [event["to"] for event in closed.json()["details"]["status_history"]] == ["under_review", "closed"]



def test_incident_status_update_rejects_stale_concurrent_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    item = SimpleNamespace(
        record_type="incident",
        status="reported",
        details={"status_history": []},
    )

    class ConflictSession:
        rolled_back = False

        def scalar(self, _statement: object) -> None:
            return None

        def execute(self, _statement: object) -> SimpleNamespace:
            return SimpleNamespace(rowcount=0)

        def rollback(self) -> None:
            self.rolled_back = True

    db = ConflictSession()
    monkeypatch.setattr(field_operations, "require_exists", lambda *_args, **_kwargs: item)
    payload = SafetyRecordUpdate(
        status="under_review",
        evidence="Assigned to the operations manager.",
    )
    user = AuthenticatedUser(
        id=UUID("00000000-0000-0000-0000-000000000071"),
        email="admin@ironhousecontracting.com",
        display_name="Test Administrator",
        role="admin",
        session_version=1,
    )

    with pytest.raises(AppError) as raised:
        field_operations.update_safety_record_status(
            db,  # type: ignore[arg-type]
            UUID("00000000-0000-0000-0000-000000000072"),
            payload,
            user,
        )

    assert raised.value.status_code == 409
    assert db.rolled_back is True

def test_first_aid_occurrences_are_management_created_and_privacy_scoped() -> None:
    worker = _employee()
    created = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "first_aid_record",
            "employee_id": worker["id"],
            "work_date": str(date.today()),
            "title": "First-aid occurrence",
            "details": {
                "occurred_at": f"{date.today()}T10:15",
                "location": "Field Operations Test",
                "first_aid_attendant": "Qualified Attendant",
                "general_nature": "Minor hand contact",
                "aid_provided": "Area was cleaned and covered.",
                "outcome": "returned_to_work",
            },
        },
    )
    assert created.status_code == 201
    record = created.json()
    assert record["status"] == "recorded"
    assert record["alert_recipients"] == []

    _authenticate_as("estimator")
    estimator_records = client.get("/api/v1/field-operations/bootstrap").json()["records"]
    assert record["id"] not in {item["id"] for item in estimator_records}
    denied = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "first_aid_record",
            "employee_id": worker["id"],
            "work_date": str(date.today()),
            "title": "Denied record",
            "details": record["details"],
        },
    )
    assert denied.status_code == 403

    _authenticate_as("admin")
    foreperson = client.post(
        "/api/v1/field-operations/employees",
        json={
            "first_name": "Field",
            "last_name": "Foreperson",
            "email": "foreperson@ironhousecontracting.com",
            "portal_role": "foreman",
        },
    )
    assert foreperson.status_code == 201

    _authenticate_as("viewer", "foreperson@ironhousecontracting.com")
    foreperson_records = client.get("/api/v1/field-operations/bootstrap").json()["records"]
    assert record["id"] not in {item["id"] for item in foreperson_records}

    _authenticate_as("viewer", worker["email"])
    worker_records = client.get("/api/v1/field-operations/bootstrap").json()["records"]
    assert record["id"] in {item["id"] for item in worker_records}


def test_foreperson_can_submit_incident_but_not_first_aid_record() -> None:
    foreperson = client.post(
        "/api/v1/field-operations/employees",
        json={
            "first_name": "Field",
            "last_name": "Foreperson",
            "email": "foreperson@ironhousecontracting.com",
            "portal_role": "foreman",
        },
    ).json()
    _authenticate_as("viewer", foreperson["email"])
    incident_payload = {
        "record_type": "incident",
        "employee_id": foreperson["id"],
        "work_date": str(date.today()),
        "title": "Crew near miss",
        "details": {
            "occurrence_kind": "near_miss",
            "occurred_at": f"{date.today()}T11:00",
            "location": "Crew work area",
            "description": "A temporary boundary was crossed.",
            "immediate_controls": "Work stopped and the boundary was reset.",
        },
    }
    incident = client.post("/api/v1/field-operations/records", json=incident_payload)
    assert incident.status_code == 201

    denied_review = client.patch(
        f"/api/v1/field-operations/records/{incident.json()['id']}/safety-status",
        json={"status": "under_review", "evidence": "Foreperson review attempt."},
    )
    assert denied_review.status_code == 403

    first_aid = client.post(
        "/api/v1/field-operations/records",
        json={
            **incident_payload,
            "record_type": "first_aid_record",
            "title": "Denied first-aid record",
            "details": {
                "occurred_at": f"{date.today()}T11:00",
                "location": "Crew work area",
                "first_aid_attendant": "Qualified Attendant",
                "general_nature": "Operational occurrence",
                "aid_provided": "First aid provided.",
                "outcome": "returned_to_work",
            },
        },
    )
    assert first_aid.status_code == 403


def test_course_ticket_expiry_creates_management_alert() -> None:
    employee = _employee()
    response = client.post(
        "/api/v1/field-operations/certifications",
        json={
            "employee_id": employee["id"],
            "name": "Ground Disturbance Level II",
            "expiry_date": str(date.today() + timedelta(days=30)),
        },
    )
    assert response.status_code == 201
    assert response.json()["expiry_status"] == "expires_soon"
    alerts = client.get("/api/v1/field-operations/bootstrap").json()["alerts"]
    assert any(alert["type"] == "ticket_expiry" for alert in alerts)


def test_safety_credentials_are_management_only_and_export_operational_status() -> None:
    employee = _employee()
    payload = {
        "employee_id": employee["id"],
        "name": "Occupational First Aid",
        "issuer": "=Approved trainer",
        "certificate_number": "FA-100",
        "issued_date": str(date.today() - timedelta(days=335)),
        "expiry_date": str(date.today() + timedelta(days=30)),
        "notes": "Renewal booking is an operational follow-up, not a compliance conclusion.",
    }

    _authenticate_as("viewer")
    denied_create = client.post("/api/v1/field-operations/certifications", json=payload)
    assert denied_create.status_code == 403
    denied_export = client.get("/api/v1/field-operations/certifications.csv")
    assert denied_export.status_code == 403

    _authenticate_as("operations_manager")
    created = client.post("/api/v1/field-operations/certifications", json=payload)
    assert created.status_code == 201
    assert created.json()["expiry_status"] == "expires_soon"

    exported = client.get("/api/v1/field-operations/certifications.csv")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "safety-credential-status.csv" in exported.headers["content-disposition"]
    assert "Crew Member" in exported.text
    assert "Occupational First Aid" in exported.text
    assert "expires_soon" in exported.text
    assert "'=Approved trainer" in exported.text


def test_job_workbook_compares_estimated_installed_and_remaining_quantities() -> None:
    project = _project()
    workspace = client.post(
        "/api/v1/estimates/workspace",
        json={
            "project_id": project["id"],
            "estimate": {
                "project_name": project["name"],
                "line_items": [{
                    "code": "03-100",
                    "description": "Storm main installation",
                    "quantity": 100,
                    "unit": "m",
                    "materials": [{"name": "PVC pipe", "quantity": 100, "unit": "m", "unit_cost": 20}],
                }],
            },
        },
    )
    assert workspace.status_code == 201

    bootstrap = client.get("/api/v1/field-operations/bootstrap").json()
    line = next(item for item in bootstrap["production_items"] if item["project_id"] == project["id"])
    assert line["estimated_quantity"] == 100
    assert line["installed_quantity"] == 0

    record = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "material_quantity",
            "project_id": project["id"],
            "cost_code": "03-100",
            "work_date": str(date.today()),
            "title": "Storm main installation",
            "details": {"line_key": line["line_key"], "installed_quantity": 35, "unit": "metre"},
        },
    )
    assert record.status_code == 201

    updated = client.get("/api/v1/field-operations/bootstrap").json()
    line = next(item for item in updated["production_items"] if item["project_id"] == project["id"])
    assert line["installed_quantity"] == 35
    assert line["remaining_quantity"] == 65
    assert line["percent_complete"] == 35


def test_material_imports_and_exports_are_tracked_by_loads_and_tonnes() -> None:
    project = _project()
    imported = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "material_movement",
            "project_id": project["id"],
            "cost_code": "02-200",
            "work_date": str(date.today()),
            "title": "Imported — 19 mm minus / road base",
            "details": {
                "direction": "imported",
                "material_code": "19mm_minus",
                "material_type": "19 mm minus / road base",
                "loads": 4,
                "tonnes_per_load": 18.5,
                "total_tonnes": 74,
            },
        },
    )
    assert imported.status_code == 201
    exported = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "material_movement",
            "project_id": project["id"],
            "cost_code": "01-300",
            "work_date": str(date.today()),
            "title": "Exported — Native material",
            "details": {
                "direction": "exported",
                "material_code": "native_material",
                "material_type": "Native material",
                "loads": 3,
                "tonnes_per_load": 16,
                "total_tonnes": 48,
            },
        },
    )
    assert exported.status_code == 201

    bootstrap = client.get("/api/v1/field-operations/bootstrap").json()
    assert any(item["code"] == "19mm_minus" for item in bootstrap["material_types"])
    imported_total = next(item for item in bootstrap["material_movement_summary"] if item["direction"] == "imported")
    exported_total = next(item for item in bootstrap["material_movement_summary"] if item["direction"] == "exported")
    assert imported_total["loads"] == 4
    assert imported_total["total_tonnes"] == 74
    assert exported_total["loads"] == 3
    assert exported_total["total_tonnes"] == 48


def test_material_movement_rejects_missing_or_zero_quantities() -> None:
    project = _project()
    response = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "material_movement",
            "project_id": project["id"],
            "work_date": str(date.today()),
            "title": "Invalid gravel movement",
            "details": {"direction": "imported", "material_type": "Pit run gravel", "loads": 0, "total_tonnes": 0},
        },
    )
    assert response.status_code == 422


def test_milestone_requires_written_and_practical_pass_before_recognition() -> None:
    employee = _employee()
    review = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "milestone_review",
            "employee_id": employee["id"],
            "work_date": str(date.today()),
            "title": "Milestone review — Green Hat Operator",
            "details": {
                "milestone_id": "operator_green_hat",
                "written_answers": {"inspection": 0, "stability": 0, "signals": 1, "loading": 0, "shutdown": 1},
            },
        },
    )
    assert review.status_code == 201
    assert review.json()["status"] == "practical_pending"
    assert review.json()["details"]["written_score"] == 100

    blocked = client.post(
        f"/api/v1/field-operations/records/{review.json()['id']}/milestone-decision",
        json={"decision": "approved", "practical_passed": False},
    )
    assert blocked.status_code == 400

    approved = client.post(
        f"/api/v1/field-operations/records/{review.json()['id']}/milestone-decision",
        json={
            "decision": "approved",
            "practical_passed": True,
            "practical_notes": "Safely completed the observed operating checklist.",
            "reward_type": "training",
            "reward_description": "Advanced excavator training day",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    recognitions = client.get("/api/v1/field-operations/bootstrap").json()["milestone_recognitions"]
    assert recognitions[0]["employee_name"] == "Crew Member"
    assert recognitions[0]["milestone_name"] == "Green Hat Operator"


def test_failed_written_milestone_test_requires_retry() -> None:
    employee = _employee()
    review = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "milestone_review",
            "employee_id": employee["id"],
            "work_date": str(date.today()),
            "title": "Milestone review — Skilled Labourer",
            "details": {
                "milestone_id": "civil_skilled_labourer",
                "written_answers": {"hazard": 0, "grade": 1, "paperwork": 2, "utility": 0, "compaction": 2},
            },
        },
    )
    assert review.status_code == 201
    assert review.json()["status"] == "written_retry_required"
    assert review.json()["details"]["written_passed"] is False


def test_bootstrap_exposes_milestone_ladders_and_on_time_paperwork_recognition() -> None:
    employee = _employee()
    project = _project()
    entry = client.post(
        "/api/v1/field-operations/time-entries",
        json={
            "employee_id": employee["id"], "project_id": project["id"], "cost_code": "02-200",
            "work_date": str(date.today()), "regular_hours": 8, "entry_type": "employee",
        },
    )
    assert entry.status_code == 201
    bootstrap = client.get("/api/v1/field-operations/bootstrap").json()
    names = {item["name"] for item in bootstrap["milestone_catalog"]}
    assert "Foreman" in names
    assert "Fine Finish Operator" in names
    paperwork = next(item for item in bootstrap["paperwork_recognitions"] if item["employee_id"] == employee["id"])
    assert paperwork["on_time_days"] == 1


def test_employee_creation_provisions_a_password_change_required_portal_account() -> None:
    response = client.post(
        "/api/v1/field-operations/employees",
        json={"first_name": "New", "last_name": "Worker", "email": "new.worker@ironhousecontracting.com", "portal_role": "employee"},
    )
    assert response.status_code == 201
    assert response.json()["portal_access_created"] is True
    temporary_password = response.json()["temporary_password"]
    assert len(temporary_password) >= 12
    login = client.post("/api/v1/auth/login", json={"email": "new.worker@ironhousecontracting.com", "password": temporary_password})
    assert login.status_code == 200
    assert login.json()["user"]["password_reset_required"] is True


def test_employee_bootstrap_is_limited_to_own_records() -> None:
    own = _employee()
    other = client.post(
        "/api/v1/field-operations/employees",
        json={"first_name": "Other", "last_name": "Worker", "email": "other.worker@ironhousecontracting.com", "portal_role": "employee"},
    ).json()

    def employee_user(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(id=UUID("00000000-0000-0000-0000-000000000009"), email=own["email"], display_name="Crew Member", role="viewer", session_version=1)
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = employee_user
    bootstrap = client.get("/api/v1/field-operations/bootstrap")
    assert bootstrap.status_code == 200
    assert [item["id"] for item in bootstrap.json()["employees"]] == [own["id"]]
    assert other["id"] not in {item["id"] for item in bootstrap.json()["employees"]}


def test_small_equipment_inspection_flags_unsafe_saw_for_management() -> None:
    employee = _employee()
    record = client.post(
        "/api/v1/field-operations/records",
        json={"record_type": "small_equipment_inspection", "employee_id": employee["id"], "work_date": str(date.today()), "title": "Cut-off saw — SAW-01", "severity": "high", "details": {"equipment_type": "Cut-off saw", "condition": "remove_from_service", "notes": "Guard damaged"}},
    )
    assert record.status_code == 201
    assert record.json()["alert_recipients"] == ["Jeremie Peters", "Mac Warren"]


def test_foreman_schedule_and_management_time_off_decision_workflow() -> None:
    employee = _employee()
    project = _project()
    shift = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "crew_shift",
            "employee_id": employee["id"],
            "project_id": project["id"],
            "work_date": str(date.today() + timedelta(days=1)),
            "title": "Scheduled shift — Field Operations Test",
            "details": {"start_time": "07:00", "end_time": "15:30", "meeting_point": "Site trailer", "notes": "Bring pipe laser"},
        },
    )
    assert shift.status_code == 201
    assert shift.json()["status"] == "scheduled"

    request = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "time_off_request",
            "employee_id": employee["id"],
            "work_date": str(date.today()),
            "title": "Time off request",
            "details": {"start_date": str(date.today() + timedelta(days=10)), "end_date": str(date.today() + timedelta(days=11)), "reason": "Appointment"},
        },
    )
    assert request.status_code == 201
    assert request.json()["status"] == "pending"
    decision = client.post(
        f"/api/v1/field-operations/records/{request.json()['id']}/time-off-decision",
        json={"decision": "approved", "management_notes": "Coverage confirmed."},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"
    assert decision.json()["details"]["management_notes"] == "Coverage confirmed."


def test_employee_cannot_schedule_or_submit_records_for_another_employee() -> None:
    own = _employee()
    other = client.post(
        "/api/v1/field-operations/employees",
        json={"first_name": "Other", "last_name": "Worker", "email": "other.schedule@ironhousecontracting.com", "portal_role": "employee"},
    ).json()
    project = _project()

    def employee_user(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(id=UUID("00000000-0000-0000-0000-000000000019"), email=own["email"], display_name="Crew Member", role="viewer", session_version=1)
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = employee_user
    try:
        shift = client.post(
            "/api/v1/field-operations/records",
            json={"record_type": "crew_shift", "employee_id": own["id"], "project_id": project["id"], "work_date": str(date.today()), "title": "Unauthorized shift", "details": {"start_time": "07:00", "end_time": "15:30"}},
        )
        assert shift.status_code == 403
        other_record = client.post(
            "/api/v1/field-operations/records",
            json={"record_type": "journal", "employee_id": other["id"], "work_date": str(date.today()), "title": "Not mine", "details": {}},
        )
        assert other_record.status_code == 403
        other_time = client.post(
            "/api/v1/field-operations/time-entries",
            json={"employee_id": other["id"], "project_id": project["id"], "cost_code": "02-200", "work_date": str(date.today()), "regular_hours": 8},
        )
        assert other_time.status_code == 403
    finally:
        app.dependency_overrides.pop(require_authenticated_user, None)


def test_time_off_request_rejects_reversed_dates() -> None:
    employee = _employee()
    response = client.post(
        "/api/v1/field-operations/records",
        json={"record_type": "time_off_request", "employee_id": employee["id"], "work_date": str(date.today()), "title": "Invalid dates", "details": {"start_date": "2026-08-10", "end_date": "2026-08-09"}},
    )
    assert response.status_code == 422


def test_purchase_order_request_is_accepted_and_returned() -> None:
    project = _project()
    payload = {
        "record_type": "purchase_order_request",
        "project_id": project["id"],
        "cost_code": "03-310",
        "work_date": str(date.today()),
        "title": "PO-12345678-FIELD-OPS-001 — PVC pipe and fittings",
        "status": "pending_approval",
        "details": {
            "po_number": "PO-12345678-FIELD-OPS-001",
            "job_number": "FIELD-OPS-001",
            "purpose": "PVC pipe and fittings",
            "amount_estimate": 1250.5,
        },
    }

    response = client.post("/api/v1/field-operations/records", json=payload)

    assert response.status_code == 201
    assert response.json()["record_type"] == "purchase_order_request"
    assert response.json()["status"] == "pending_approval"
    bootstrap = client.get("/api/v1/field-operations/bootstrap")
    assert bootstrap.status_code == 200
    stored = next(
        item
        for item in bootstrap.json()["records"]
        if item["id"] == response.json()["id"]
    )
    assert stored["details"]["po_number"] == "PO-12345678-FIELD-OPS-001"
