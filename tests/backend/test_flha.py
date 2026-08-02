from copy import deepcopy
from datetime import UTC, date, datetime
from io import BytesIO
from uuid import UUID
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser
import app.services.file_storage as file_storage
from app.services.file_storage import LocalFileStorageProvider


client = TestClient(app)
SCREENING_KEYS = [
    "first_aid_equipment",
    "overhead_hazards",
    "underground_utilities_locates",
    "mobile_equipment",
    "confined_space",
    "excavation_sloping_shoring_access",
    "additional_ppe",
    "traffic_control",
    "subcontractors",
    "basic_ppe_review",
]


def _employee(email: str, portal_role: str = "employee") -> dict:
    response = client.post(
        "/api/v1/field-operations/employees",
        json={
            "first_name": email.split("@")[0].split(".")[0].title(),
            "last_name": "Worker",
            "email": email,
            "portal_role": portal_role,
            "provision_portal_access": False,
        },
    )
    assert response.status_code == 201
    return response.json()


def _project() -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": "FLHA Acceptance Project", "project_number": "FLHA-127"},
    )
    assert response.status_code == 201
    return response.json()


def _details(employee: dict, *, controlled: bool = True, evidence: bool = False) -> dict:
    return {
        "site_location": "North utility tie-in",
        "started_at": datetime.now(UTC).isoformat(),
        "supervisor_name": "Site Foreperson",
        "first_aid_attendant": "First Aid Attendant",
        "crew": [
            {
                "employee_id": employee["id"],
                "employee_name": employee["first_name"] + " " + employee["last_name"],
            }
        ],
        "weather": "Dry, 18 C, light wind",
        "screening": [{"key": key, "response": "yes", "notes": None} for key in SCREENING_KEYS],
        "tasks": [
            {
                "id": "task-1",
                "task": "Excavate utility trench",
                "hazard": "Cave-in and utility strike",
                "control": "Verify locates, shoring, access and exclusion zone" if controlled else "",
                "control_hierarchy": "engineering",
                "responsible_person": "Site Foreperson" if controlled else "",
                "critical": True,
                "control_accepted": controlled,
                "evidence_required": evidence,
                "evidence_ids": ["00000000-0000-0000-0000-000000000127"] if evidence else [],
                "ai_suggested": False,
            }
        ],
        "emergency_response": "Stop work, call emergency services and notify the supervisor.",
        "muster_point": "Site entrance sign",
        "communication_method": "Radio channel 2 and mobile phone",
        "stop_work_triggers": ["Conditions change", "Control is ineffective"],
        "preset_names": ["Excavation and utilities"],
    }


def _create(project: dict, employee: dict, details: dict) -> dict:
    response = client.post(
        "/api/v1/field-operations/flha",
        json={
            "project_id": project["id"],
            "work_date": str(date.today()),
            "title": "Daily FLHA - utility tie-in",
            "details": details,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _authenticate(email: str, role: str = "viewer", name: str = "Portal Worker") -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000099"),
            email=email,
            display_name=name,
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def test_flha_create_edit_release_sign_reassess_audit_and_immutability() -> None:
    employee = _employee("crew.flha@ironhousecontracting.com")
    project = _project()
    details = _details(employee)
    record = _create(project, employee, details)

    assert record["status"] == "draft"
    assert record["details"]["ai_advisory_only"] is True
    assert record["details"]["audit_trail"][0]["action"] == "created"

    edited = deepcopy(details)
    edited["weather"] = "Cloud increasing, 17 C"
    response = client.patch(
        f"/api/v1/field-operations/flha/{record['id']}",
        json={"details": edited, "change_summary": "Updated observed weather"},
    )
    assert response.status_code == 200
    assert response.json()["details"]["audit_trail"][-1]["action"] == "edited"

    response = client.post(
        f"/api/v1/field-operations/flha/{record['id']}/release",
        json={"field_conditions_verified": True, "release_note": "Conditions verified at work location."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "released"
    assert response.json()["details"]["audit_trail"][-1]["action"] == "supervisor_released"

    immutable = client.patch(
        f"/api/v1/field-operations/flha/{record['id']}",
        json={"details": details, "change_summary": "Attempt to alter released content"},
    )
    assert immutable.status_code == 409
    assert "immutable" in immutable.json()["error"]["message"]

    signed = client.post(
        f"/api/v1/field-operations/flha/{record['id']}/sign",
        json={
            "employee_id": employee["id"],
            "employee_name": "Crew Worker",
            "acknowledgement": "I reviewed the hazards and controls and will stop work if conditions change.",
            "supervised_shared_device": True,
        },
    )
    assert signed.status_code == 200
    assert signed.json()["status"] == "signed"
    assert signed.json()["signatures"][0]["supervised_shared_device"] is True

    reassessed_details = deepcopy(details)
    reassessed_details["weather"] = "Rain beginning; trench conditions reassessed"
    reassessed = client.post(
        f"/api/v1/field-operations/flha/{record['id']}/reassess",
        json={"reason": "Weather materially changed", "details": reassessed_details},
    )
    assert reassessed.status_code == 201
    assert reassessed.json()["id"] != record["id"]
    assert reassessed.json()["details"]["flha_version"] == 2
    assert reassessed.json()["details"]["source_record_id"] == record["id"]
    assert reassessed.json()["signatures"] == []

    original = client.get(f"/api/v1/field-operations/flha/{record['id']}")
    assert original.status_code == 200
    assert original.json()["status"] == "signed"
    assert original.json()["details"]["flha_version"] == 1


def test_critical_hazard_without_controls_responsible_person_or_evidence_stays_blocked() -> None:
    employee = _employee("blocked.flha@ironhousecontracting.com")
    project = _project()
    details = _details(employee, controlled=False, evidence=True)
    record = _create(project, employee, details)

    assert record["status"] == "blocked"
    blockers = " ".join(record["details"]["release_blockers"])
    assert "control" in blockers
    assert "responsible person" in blockers
    assert "evidence" in blockers

    release = client.post(
        f"/api/v1/field-operations/flha/{record['id']}/release",
        json={"field_conditions_verified": True},
    )
    assert release.status_code == 409
    assert "remains blocked" in release.json()["error"]["message"]




def test_only_guarded_routes_can_create_or_sign_flha_records() -> None:
    employee = _employee("guarded.flha@ironhousecontracting.com")
    project = _project()
    generic_create = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "daily_hazard_assessment",
            "project_id": project["id"],
            "employee_id": employee["id"],
            "work_date": str(date.today()),
            "title": "Bypass attempt",
            "details": {},
        },
    )
    assert generic_create.status_code == 422
    assert "guarded FLHA" in generic_create.json()["error"]["message"]

    guarded = _create(project, employee, _details(employee))
    generic_sign = client.post(
        f"/api/v1/field-operations/records/{guarded['id']}/sign",
        json={
            "employee_id": employee["id"],
            "employee_name": "Guarded Worker",
            "acknowledgement": "Attempting to bypass supervisor release.",
        },
    )
    assert generic_sign.status_code == 422
    assert "guarded FLHA" in generic_sign.json()["error"]["message"]


def test_required_evidence_must_be_authorized_linked_media_and_freezes_on_release(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(file_storage, "storage_provider", LocalFileStorageProvider(tmp_path))
    employee = _employee("evidence.flha@ironhousecontracting.com")
    project = _project()
    details = _details(employee, evidence=True)
    record = _create(project, employee, details)
    assert record["status"] == "blocked"

    asset_response = client.post(
        "/api/v1/media",
        data={"category": "flha", "caption": "Shoring and locate evidence", "project_id": project["id"]},
        files=[("files", ("evidence.jpg", BytesIO(b"immutable-flha-evidence"), "image/jpeg"))],
    )
    assert asset_response.status_code == 201
    asset = asset_response.json()[0]
    linked = client.post(
        f"/api/v1/media/{asset['id']}/links",
        json={"record_type": "field_record", "record_id": record["id"]},
    )
    assert linked.status_code == 200

    details["tasks"][0]["evidence_ids"] = [asset["id"]]
    updated = client.patch(
        f"/api/v1/field-operations/flha/{record['id']}",
        json={"details": details, "change_summary": "Linked required shoring evidence"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "draft"
    released = client.post(
        f"/api/v1/field-operations/flha/{record['id']}/release",
        json={"field_conditions_verified": True},
    )
    assert released.status_code == 200

    metadata_change = client.patch(
        f"/api/v1/media/{asset['id']}",
        json={"caption": "Attempted signed evidence change"},
    )
    assert metadata_change.status_code == 409
    assert "immutable" in metadata_change.json()["error"]["message"]

    second_asset = client.post(
        "/api/v1/media",
        data={"category": "flha", "caption": "Late evidence", "project_id": project["id"]},
        files=[("files", ("late.jpg", BytesIO(b"late-evidence"), "image/jpeg"))],
    ).json()[0]
    late_link = client.post(
        f"/api/v1/media/{second_asset['id']}/links",
        json={"record_type": "field_record", "record_id": record["id"]},
    )
    assert late_link.status_code == 409

def test_ai_suggestions_are_advisory_and_do_not_complete_or_mutate_flha() -> None:
    response = client.post(
        "/api/v1/field-operations/flha/suggestions",
        json={"task": "Excavate trench beside utility"},
    )
    assert response.status_code == 200
    assert response.json()[0]["advisory_only"] is True
    assert "status" not in response.json()[0]


def test_employee_permission_scope_and_own_device_signature() -> None:
    own = _employee("own.flha@ironhousecontracting.com")
    other = _employee("other.flha@ironhousecontracting.com")
    project = _project()
    _authenticate(own["email"])

    forbidden = client.post(
        "/api/v1/field-operations/flha",
        json={
            "project_id": project["id"],
            "work_date": str(date.today()),
            "details": {
                **_details(own),
                "crew": [
                    {"employee_id": own["id"], "employee_name": "Own Worker"},
                    {"employee_id": other["id"], "employee_name": "Other Worker"},
                ],
            },
        },
    )
    assert forbidden.status_code == 403

    own_record = _create(project, own, _details(own))
    release = client.post(
        f"/api/v1/field-operations/flha/{own_record['id']}/release",
        json={"field_conditions_verified": True},
    )
    assert release.status_code == 403




def test_listed_crew_member_can_discover_and_read_foreperson_flha() -> None:
    foreperson = _employee("listing.foreman@ironhousecontracting.com", "foreman")
    worker = _employee("listing.worker@ironhousecontracting.com")
    project = _project()
    details = _details(foreperson)
    details["crew"].append(
        {
            "employee_id": worker["id"],
            "employee_name": worker["first_name"] + " " + worker["last_name"],
        }
    )
    record = _create(project, foreperson, details)

    _authenticate(worker["email"])
    response = client.get("/api/v1/field-operations/bootstrap")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["records"]] == [record["id"]]
    assert client.get(f"/api/v1/field-operations/flha/{record['id']}").status_code == 200

def test_compact_pdf_has_no_blank_pages_and_keeps_signature_rows_intact() -> None:
    employee = _employee("pdf.flha@ironhousecontracting.com")
    project = _project()
    record = _create(project, employee, _details(employee))
    client.post(
        f"/api/v1/field-operations/flha/{record['id']}/release",
        json={"field_conditions_verified": True},
    )
    client.post(
        f"/api/v1/field-operations/flha/{record['id']}/sign",
        json={
            "employee_id": employee["id"],
            "employee_name": "Pdf Worker",
            "acknowledgement": "I reviewed and accept the listed controls for this work.",
            "supervised_shared_device": True,
        },
    )

    response = client.get(f"/api/v1/field-operations/flha/{record['id']}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    reader = PdfReader(BytesIO(response.content))
    assert reader.pages
    extracted = [page.extract_text() or "" for page in reader.pages]
    assert all(page.strip() for page in extracted)
    text = "\n".join(extracted)
    assert "CREW ACKNOWLEDGEMENTS" in text
    assert "Pdf Worker | Signed" in text

