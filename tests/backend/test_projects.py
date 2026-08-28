from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.field_operations import FieldRecord
from app.models.project import Project, ProjectCloseoutChecklistItem, ProjectStartChecklistItem
from app.services.auth import AuthenticatedUser
from app.services.projects import (
    _provision_project_closeout_checklist,
    _provision_project_start_checklist,
)
from conftest import TestingSessionLocal


client = TestClient(app)
IRON_HOUSE_TIME_ZONE = ZoneInfo("America/Vancouver")


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000088"),
            email=f"{role}@ironhousecontracting.com",
            display_name=f"Test {role.replace('_', ' ').title()}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def create_project(name: str = "King George Utility Upgrade") -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "client_owner": "City of Surrey",
            "municipality": "Surrey",
            "project_number": "IHO-1001",
            "tender_number": "T-2026-001",
            "tender_source": "BC Bid",
            "tender_closing_date": "2026-08-01",
            "bid_due_date": "2026-07-25",
            "estimated_construction_start": "2026-09-01",
            "estimated_construction_finish": "2027-02-01",
            "project_address": "100 King George Blvd",
            "latitude": 49.1913,
            "longitude": -122.849,
            "contract_value": 1250000,
            "status": "opportunity",
            "notes": "Phase 4 project workspace test.",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_supplier() -> dict:
    response = client.post("/api/v1/suppliers", json={"name": "Pacific Pipe Supply"})
    assert response.status_code == 201
    return response.json()


def test_create_project() -> None:
    project = create_project()

    assert project["name"] == "King George Utility Upgrade"
    assert project["municipality"] == "Surrey"
    assert project["status"] == "opportunity"
    assert project["workspace_root"] is None


def test_awarded_project_creation_generates_sequential_job_numbers() -> None:
    year = datetime.now(IRON_HOUSE_TIME_ZONE).year

    first = client.post("/api/v1/projects", json={"name": "First Award", "status": "awarded"})
    second = client.post("/api/v1/projects", json={"name": "Second Award", "status": "awarded"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["project_number"] == f"IH{year}001"
    assert second.json()["project_number"] == f"IH{year}002"
    assert first.json()["workspace_root"] == f"IH{year}001_FirstAward"
    assert second.json()["workspace_root"] == f"IH{year}002_SecondAward"


def test_new_awarded_project_has_evidence_backed_closeout_controls() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Closeout Controlled Award", "status": "awarded"},
    ).json()

    response = client.get(f"/api/v1/projects/{project['id']}/closeout-checklist")

    assert response.status_code == 200
    checklist = response.json()
    assert checklist["status"] == "not_ready"
    assert checklist["completed_count"] == 0
    assert checklist["total_count"] == 10
    assert checklist["next_incomplete_control"]["code"] == "deficiencies"
    assert [item["code"] for item in checklist["items"]] == [
        "deficiencies",
        "testing_inspections",
        "permit_authority_finals",
        "asbuilts_redlines",
        "turnover_warranty",
        "demobilization",
        "changes_commitments",
        "billing_holdback",
        "acceptance_evidence",
        "turnover_index",
    ]


def test_project_completion_requires_all_closeout_evidence_and_management() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Controlled Completion", "status": "awarded"},
    ).json()
    construction = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "construction"},
    )
    assert construction.status_code == 200

    blocked = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "completed"},
    )
    assert blocked.status_code == 409
    assert "every project closeout control" in blocked.json()["error"]["message"]

    checklist = client.get(f"/api/v1/projects/{project['id']}/closeout-checklist").json()
    missing_evidence = client.patch(
        f"/api/v1/projects/{project['id']}/closeout-checklist/{checklist['items'][0]['code']}",
        json={"completed": True},
    )
    assert missing_evidence.status_code == 422

    for item in checklist["items"]:
        updated = client.patch(
            f"/api/v1/projects/{project['id']}/closeout-checklist/{item['code']}",
            json={
                "completed": True,
                "evidence": f"Controlled source record for {item['code']}",
            },
        )
        assert updated.status_code == 200

    ready = updated.json()
    assert ready["status"] == "ready"
    assert ready["completed_count"] == ready["total_count"] == 10
    assert ready["next_incomplete_control"] is None
    assert all(item["changed_by"] == "test-admin@ironhousecontracting.com" for item in ready["items"])
    assert all(item["changed_at"] for item in ready["items"])

    _authenticate_as("estimator")
    denied = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "completed"},
    )
    assert denied.status_code == 403

    _authenticate_as("operations_manager")
    completed = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    completion = completed.json()["metadata"]["closeout_completion"]
    assert completion["completed_by"] == "operations_manager@ironhousecontracting.com"
    assert completion["completed_at"]

    cannot_reopen_item = client.patch(
        f"/api/v1/projects/{project['id']}/closeout-checklist/deficiencies",
        json={"completed": False},
    )
    assert cannot_reopen_item.status_code == 409

    reopened = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "construction"},
    )
    assert reopened.status_code == 200
    reopening = reopened.json()["metadata"]["closeout_reopening"]
    assert reopening["reopened_by"] == "operations_manager@ironhousecontracting.com"
    assert reopening["reopened_at"]
    assert reopening["reopened_to_status"] == "construction"

    reopened_item = client.patch(
        f"/api/v1/projects/{project['id']}/closeout-checklist/deficiencies",
        json={"completed": False},
    )
    assert reopened_item.status_code == 200
    assert reopened_item.json()["items"][0]["evidence"] is None


def test_management_can_initialize_legacy_job_closeout_without_automatic_backfill() -> None:
    with TestingSessionLocal() as db:
        project = Project(
            name="Legacy Construction Job",
            status="construction",
            project_number="IH2025001",
        )
        db.add(project)
        db.commit()
        project_id = project.id

    assert client.get(f"/api/v1/projects/{project_id}/closeout-checklist").status_code == 404

    _authenticate_as("viewer")
    assert client.post(f"/api/v1/projects/{project_id}/closeout-checklist").status_code == 403

    _authenticate_as("operations_manager")
    initialized = client.post(f"/api/v1/projects/{project_id}/closeout-checklist")
    assert initialized.status_code == 201
    assert initialized.json()["total_count"] == 10
    assert initialized.json()["completed_count"] == 0


def test_project_cannot_be_created_directly_as_completed() -> None:
    response = client.post(
        "/api/v1/projects",
        json={"name": "Bypassed Closeout", "status": "completed"},
    )

    assert response.status_code == 409


def test_transition_to_awarded_generates_job_number() -> None:
    year = datetime.now(IRON_HOUSE_TIME_ZONE).year
    project = client.post("/api/v1/projects", json={"name": "Tender Without Number"}).json()

    response = client.patch(f"/api/v1/projects/{project['id']}", json={"status": "awarded"})

    assert response.status_code == 200
    assert response.json()["status"] == "awarded"
    assert response.json()["project_number"] == f"IH{year}001"
    assert response.json()["workspace_root"] == f"IH{year}001_TenderWithoutNumber"

    workspace = client.get(f"/api/v1/projects/{project['id']}/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["job_number"] == f"IH{year}001"
    assert any(entry["path"].endswith("/13_Award_Handoff") for entry in workspace.json()["entries"])

    checklist = client.get(f"/api/v1/projects/{project['id']}/start-checklist")
    assert checklist.status_code == 200
    assert checklist.json()["status"] == "not_ready"
    assert checklist.json()["completed_count"] == 0
    assert checklist.json()["total_count"] == 10


def test_awarded_safety_launch_is_blocked_typed_idempotent_and_does_not_create_evidence() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Controlled Safety Launch", "status": "awarded"},
    ).json()

    first = client.post(f"/api/v1/projects/{project['id']}/safety-launch")
    read_back = client.get(f"/api/v1/projects/{project['id']}/safety-launch")
    retry = client.post(f"/api/v1/projects/{project['id']}/safety-launch")
    workspace = client.get(f"/api/v1/projects/{project['id']}/workspace").json()
    checklist = client.get(f"/api/v1/projects/{project['id']}/start-checklist").json()

    assert first.status_code == 201
    assert read_back.status_code == 200
    assert retry.status_code == 201
    assert read_back.json() == first.json()
    assert retry.json() == first.json()
    launch = first.json()
    assert launch["job_number"] == project["project_number"]
    assert launch["release_status"] == "blocked"
    assert launch["folder_status"] == "prepared"
    assert launch["folder_path"].endswith("/13_Award_Handoff/Safety")
    assert len(launch["record_requirements"]) == 6
    assert all(item["applicability_status"] == "unconfirmed" for item in launch["record_requirements"])
    assert all(item["status"] == "not_started" for item in launch["record_requirements"])
    assert all(item["record_id"] is None for item in launch["record_requirements"])
    assert all(item["evidence_document_ids"] == [] for item in launch["record_requirements"])
    assert launch["portal_access"] == {
        "status": "not_started",
        "automatic_provisioning": False,
        "assignments": [],
    }
    assert sum(entry["path"] == launch["folder_path"] for entry in workspace["entries"]) == 1
    assert checklist["completed_count"] == 0
    with TestingSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(FieldRecord)
            .where(FieldRecord.project_id == UUID(project["id"]))
        ) == 0


def test_safety_launch_initialization_requires_management() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Management Safety Launch", "status": "awarded"},
    ).json()

    _authenticate_as("viewer")

    assert client.get(f"/api/v1/projects/{project['id']}/safety-launch").status_code == 403
    assert client.post(f"/api/v1/projects/{project['id']}/safety-launch").status_code == 403


def test_safety_launch_metadata_cannot_be_injected_or_changed_by_generic_project_writes() -> None:
    injected = client.post(
        "/api/v1/projects",
        json={
            "name": "Injected Safety Launch",
            "status": "awarded",
            "metadata": {"safety_launch": {"release_status": "ready"}},
        },
    )
    assert injected.status_code == 409

    project = client.post(
        "/api/v1/projects",
        json={"name": "Protected Safety Metadata", "status": "awarded"},
    ).json()
    launch = client.post(f"/api/v1/projects/{project['id']}/safety-launch").json()
    changed = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"metadata": {"safety_launch": {**launch, "release_status": "ready"}}},
    )
    assert changed.status_code == 409

    unrelated = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"metadata": {"management_note": "Safety launch remains controlled."}},
    )
    assert unrelated.status_code == 200
    assert unrelated.json()["metadata"]["management_note"] == "Safety launch remains controlled."
    assert unrelated.json()["metadata"]["safety_launch"] == launch


def test_awarded_job_start_checklist_records_checkbox_state_and_actor() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Checklist Award", "status": "awarded"},
    ).json()

    checklist = client.get(f"/api/v1/projects/{project['id']}/start-checklist")

    assert checklist.status_code == 200
    assert [item["code"] for item in checklist.json()["items"]] == [
        "award_contract",
        "scope_review",
        "current_documents",
        "contacts_authority",
        "budget_cost_codes",
        "schedule_milestones",
        "procurement_plan",
        "permits_insurance_bonding",
        "safety_mobilization",
        "quality_testing_asbuilts",
    ]

    completed = client.patch(
        f"/api/v1/projects/{project['id']}/start-checklist/award_contract",
        json={"completed": True},
    )

    assert completed.status_code == 200
    assert completed.json()["status"] == "not_ready"
    assert completed.json()["completed_count"] == 1
    first_item = completed.json()["items"][0]
    assert first_item["completed"] is True
    assert first_item["changed_by"] == "test-admin@ironhousecontracting.com"
    assert first_item["changed_at"] is not None

    reopened = client.patch(
        f"/api/v1/projects/{project['id']}/start-checklist/award_contract",
        json={"completed": False},
    )

    assert reopened.status_code == 200
    assert reopened.json()["completed_count"] == 0
    assert reopened.json()["items"][0]["completed"] is False


def test_awarded_job_start_readiness_is_derived_and_provisioning_is_idempotent() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Ready Award", "status": "awarded"},
    ).json()
    checklist = client.get(f"/api/v1/projects/{project['id']}/start-checklist").json()

    for item in checklist["items"]:
        response = client.patch(
            f"/api/v1/projects/{project['id']}/start-checklist/{item['code']}",
            json={"completed": True},
        )
        assert response.status_code == 200

    completed = response.json()
    assert completed["status"] == "ready"
    assert completed["completed_count"] == completed["total_count"] == 10

    client.patch(f"/api/v1/projects/{project['id']}", json={"status": "construction"})
    client.patch(f"/api/v1/projects/{project['id']}", json={"status": "awarded"})
    reprovisioned = client.get(f"/api/v1/projects/{project['id']}/start-checklist").json()

    assert reprovisioned["total_count"] == 10
    assert reprovisioned["completed_count"] == 10


def test_checklist_provisioning_is_conflict_safe_before_commit() -> None:
    with TestingSessionLocal() as db:
        project = Project(
            name="Concurrent Checklist Award",
            status="awarded",
            project_number="IH-2026-099",
        )
        db.add(project)
        db.flush()

        _provision_project_start_checklist(db, project.id)
        _provision_project_start_checklist(db, project.id)
        db.flush()

        count = db.scalar(
            select(func.count())
            .select_from(ProjectStartChecklistItem)
            .where(ProjectStartChecklistItem.project_id == project.id)
        )

    assert count == 10


def test_closeout_checklist_provisioning_is_conflict_safe_before_commit() -> None:
    with TestingSessionLocal() as db:
        project = Project(
            name="Concurrent Closeout Checklist",
            status="awarded",
            project_number="IH2026099",
        )
        db.add(project)
        db.flush()

        _provision_project_closeout_checklist(db, project.id)
        _provision_project_closeout_checklist(db, project.id)
        db.flush()

        count = db.scalar(
            select(func.count())
            .select_from(ProjectCloseoutChecklistItem)
            .where(ProjectCloseoutChecklistItem.project_id == project.id)
        )

    assert count == 10


def test_non_awarded_project_has_no_start_checklist() -> None:
    project = client.post("/api/v1/projects", json={"name": "Open Tender"}).json()

    response = client.get(f"/api/v1/projects/{project['id']}/start-checklist")

    assert response.status_code == 404


def test_legacy_awarded_project_is_not_backfilled_by_an_ordinary_update() -> None:
    with TestingSessionLocal() as db:
        project = Project(
            name="Legacy Award Without Checklist",
            status="awarded",
            project_number="LEGACY-2025-001",
            workspace_root="LEGACY-2025-001_LegacyAwardWithoutChecklist",
            workspace_manifest_json={"legacy": True},
            workspace_provisioned_at=datetime.now(UTC),
        )
        db.add(project)
        db.commit()
        project_id = project.id

    before_update = client.get(f"/api/v1/projects/{project_id}/start-checklist")
    updated = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Legacy Award Renamed"},
    )
    after_update = client.get(f"/api/v1/projects/{project_id}/start-checklist")

    assert before_update.status_code == 404
    assert updated.status_code == 200
    assert updated.json()["name"] == "Legacy Award Renamed"
    assert after_update.status_code == 404


def test_award_generation_skips_existing_numbers_and_preserves_explicit_number() -> None:
    year = datetime.now(IRON_HOUSE_TIME_ZONE).year
    explicit = client.post(
        "/api/v1/projects",
        json={"name": "Existing Award", "status": "awarded", "project_number": f"IH-{year}-009"},
    )
    generated = client.post("/api/v1/projects", json={"name": "Next Award", "status": "awarded"})

    assert explicit.status_code == 201
    assert explicit.json()["project_number"] == f"IH-{year}-009"
    assert explicit.json()["workspace_root"] == f"IH-{year}-009_ExistingAward"
    assert generated.status_code == 201
    assert generated.json()["project_number"] == f"IH{year}010"


def test_award_generation_retries_a_unique_collision() -> None:
    year = datetime.now(IRON_HOUSE_TIME_ZONE).year
    duplicate = f"IH-{year}-001"
    available = f"IH-{year}-002"
    client.post(
        "/api/v1/projects",
        json={"name": "Existing Number", "status": "awarded", "project_number": duplicate},
    )

    with patch("app.services.projects._next_job_number", side_effect=[duplicate, available]):
        response = client.post(
            "/api/v1/projects", json={"name": "Concurrent Award", "status": "awarded"}
        )

    assert response.status_code == 201
    assert response.json()["project_number"] == available


def test_assigned_job_number_is_not_removed_or_replaced_by_project_update() -> None:
    project = client.post(
        "/api/v1/projects",
        json={
            "name": "Award With Custom Number",
            "status": "awarded",
            "project_number": "CLIENT-JOB-77",
        },
    ).json()

    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"project_number": None, "status": "construction"},
    )

    assert response.status_code == 200
    assert response.json()["project_number"] == "CLIENT-JOB-77"
    assert response.json()["status"] == "construction"


def test_awarded_workspace_is_provisioned_once_and_keeps_its_original_root() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Original Tender Name", "status": "tendering"},
    ).json()
    awarded = client.patch(f"/api/v1/projects/{project['id']}", json={"status": "awarded"}).json()
    original_root = awarded["workspace_root"]
    original_provisioned_at = awarded["workspace_provisioned_at"]

    updated = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Renamed During Construction", "status": "construction"},
    ).json()
    workspace = client.get(f"/api/v1/projects/{project['id']}/workspace").json()

    assert updated["workspace_root"] == original_root
    assert updated["workspace_provisioned_at"] == original_provisioned_at
    assert workspace["root_folder"] == original_root
    assert workspace["project_index"].startswith("# Project Index\n\nJob Number:")


def test_non_awarded_project_has_no_provisioned_workspace() -> None:
    project = client.post("/api/v1/projects", json={"name": "Open Tender"}).json()

    response = client.get(f"/api/v1/projects/{project['id']}/workspace")

    assert project["workspace_root"] is None
    assert project["workspace_provisioned_at"] is None
    assert response.status_code == 404


def test_list_project_and_detail() -> None:
    project = create_project()

    list_response = client.get("/api/v1/projects")
    detail_response = client.get(f"/api/v1/projects/{project['id']}")

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert detail_response.json()["project_number"] == "IHO-1001"


def test_update_project() -> None:
    project = create_project()

    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "tendering", "municipality": "Burnaby", "notes": "Updated notes."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "tendering"
    assert response.json()["municipality"] == "Burnaby"
    assert response.json()["notes"] == "Updated notes."


def test_archive_project() -> None:
    project = create_project()

    response = client.post(f"/api/v1/projects/{project['id']}/archive")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_project_relationships_and_dashboard_summary() -> None:
    supplier = create_supplier()
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Relationship Project", "supplier_ids": [supplier["id"]]},
    )
    project = project_response.json()
    client.post(
        "/api/v1/rfqs",
        json={"title": "Pipe RFQ", "project_id": project["id"], "scope_summary": "Pipe supply."},
    )
    client.post(
        "/api/v1/documents",
        json={"title": "C-101", "category": "drawing", "project_id": project["id"]},
    )

    response = client.get(f"/api/v1/projects/{project['id']}/dashboard")

    assert response.status_code == 200
    assert response.json()["rfq_count"] == 1
    assert response.json()["supplier_count"] == 1
    assert response.json()["document_count"] == 1
    assert response.json()["drawing_count"] == 1
    assert response.json()["readiness_percentage"] == 80
    assert project["supplier_ids"] == [supplier["id"]]


def test_missing_project_returns_404() -> None:
    response = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
