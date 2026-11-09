from datetime import date
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.bid import Bid
from app.models.document import Document
from app.models.field_operations import FieldRecord
from app.models.finance import FinancialEntry
from app.services.auth import AuthenticatedUser
from conftest import TestingSessionLocal, override_authenticated_user


client = TestClient(app)


def create_awarded_project(name: str = "Launch Dashboard Job") -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": name, "status": "awarded"},
    )
    assert response.status_code == 201
    return response.json()


def test_awarded_project_launch_dashboard_starts_with_derived_controls() -> None:
    project = create_awarded_project()

    response = client.get(f"/api/v1/projects/{project['id']}/launch-dashboard")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": project["id"],
        "job_number": project["project_number"],
        "mobilization_status": "not_ready",
        "checklist_completed_count": 0,
        "checklist_total_count": 10,
        "next_incomplete_control": {
            "code": "award_contract",
            "category": "Contract",
            "label": "Award notice or executed contract and the client scope record are saved.",
        },
        "estimate_workspace_count": 0,
        "priced_estimate_available": False,
        "baseline_budget_total": 0.0,
        "budget_entry_count": 0,
        "po_request_count": 0,
        "pending_po_request_count": 0,
        "safety_record_counts": {
            "safety_permit": 0,
            "emergency_action_card": 0,
            "daily_hazard_assessment": 0,
            "toolbox_talk": 0,
            "corrective_action": 0,
        },
        "safety_release_status": "not_initialized",
        "safety_requirement_count": 0,
        "safety_folder_status": "not_initialized",
        "portal_access_status": "not_initialized",
        "portal_assignment_count": 0,
        "production_posting_status": "blocked",
        "production_blockers": ["safety_launch", "mobilization"],
        "daily_sheet_count": 0,
        "production_post_count": 0,
        "latest_daily_sheet_status": "not_started",
        "field_production_folder_status": "not_initialized",
        "document_count": 0,
        "award_baseline_source": None,
        "award_pricing_subtotal": 0.0,
        "award_cost_budget_status": "not_started",
        "uncoded_award_line_count": 0,
        "procurement_requirement_count": 0,
        "procurement_plan_status": "not_started",
    }


def test_launch_dashboard_summarizes_existing_source_records_without_inferred_approval() -> None:
    project = create_awarded_project("Populated Launch Job")
    project_id = UUID(project["id"])

    with TestingSessionLocal() as db:
        db.add_all(
            [
                Bid(
                    project_id=project_id,
                    status="draft",
                    total_amount=125000,
                    summary="Priced estimate",
                    bid_json={"summary": {"total": 125000}},
                ),
                FinancialEntry(
                    project_id=project_id,
                    cost_code="01-100",
                    entry_type="budget",
                    category="labour",
                    amount=75000,
                    entry_date=date(2026, 8, 21),
                    source_type="estimate",
                    status="posted",
                    metadata_json={},
                    created_by="test-admin@ironhousecontracting.com",
                ),
                FinancialEntry(
                    project_id=project_id,
                    cost_code="02-100",
                    entry_type="budget",
                    category="materials",
                    amount=25000,
                    entry_date=date(2026, 8, 21),
                    source_type="estimate",
                    status="void",
                    metadata_json={},
                    created_by="test-admin@ironhousecontracting.com",
                ),
                FieldRecord(
                    record_type="purchase_order_request",
                    project_id=project_id,
                    work_date=date(2026, 8, 21),
                    title="Pipe and fittings",
                    status="pending_approval",
                    severity="none",
                    details={},
                    document_ids=[],
                    signatures=[],
                    alert_recipients=[],
                ),
                FieldRecord(
                    record_type="purchase_order_request",
                    project_id=project_id,
                    work_date=date(2026, 8, 21),
                    title="Aggregate",
                    status="approved",
                    severity="none",
                    details={},
                    document_ids=[],
                    signatures=[],
                    alert_recipients=[],
                ),
                FieldRecord(
                    record_type="safety_permit",
                    project_id=project_id,
                    work_date=date(2026, 8, 21),
                    title="Ground disturbance permit",
                    status="ready",
                    severity="high",
                    details={},
                    document_ids=[],
                    signatures=[],
                    alert_recipients=[],
                ),
                FieldRecord(
                    record_type="toolbox_talk",
                    project_id=project_id,
                    work_date=date(2026, 8, 21),
                    title="Mobilization talk",
                    status="submitted",
                    severity="none",
                    details={},
                    document_ids=[],
                    signatures=[],
                    alert_recipients=[],
                ),
                FieldRecord(
                    record_type="incident",
                    project_id=project_id,
                    work_date=date(2026, 8, 21),
                    title="Confidential occurrence",
                    status="reported",
                    severity="high",
                    details={"occurrence_kind": "incident"},
                    document_ids=[],
                    signatures=[],
                    alert_recipients=[],
                ),
                Document(
                    project_id=project_id,
                    title="Issued for construction drawing",
                    category="drawing",
                    status="registered",
                    metadata_json={},
                ),
            ]
        )
        db.commit()

    response = client.get(f"/api/v1/projects/{project['id']}/launch-dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["priced_estimate_available"] is True
    assert body["estimate_workspace_count"] == 1
    assert body["baseline_budget_total"] == 75000.0
    assert body["budget_entry_count"] == 1
    assert body["po_request_count"] == 2
    assert body["pending_po_request_count"] == 1
    assert body["safety_record_counts"]["safety_permit"] == 1
    assert body["safety_record_counts"]["toolbox_talk"] == 1
    assert "incident" not in body["safety_record_counts"]
    assert body["document_count"] == 1
    assert body["mobilization_status"] == "not_ready"


def test_launch_dashboard_readiness_follows_only_the_project_start_checklist() -> None:
    project = create_awarded_project("Ready Launch Job")
    checklist = client.get(f"/api/v1/projects/{project['id']}/start-checklist").json()

    for item in checklist["items"]:
        response = client.patch(
            f"/api/v1/projects/{project['id']}/start-checklist/{item['code']}",
            json={"completed": True},
        )
        assert response.status_code == 200

    response = client.get(f"/api/v1/projects/{project['id']}/launch-dashboard")

    assert response.status_code == 200
    assert response.json()["mobilization_status"] == "ready"
    assert response.json()["checklist_completed_count"] == 10
    assert response.json()["next_incomplete_control"] is None


def test_launch_dashboard_rejects_non_awarded_projects() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Still Tendering", "status": "tendering"},
    ).json()

    response = client.get(f"/api/v1/projects/{project['id']}/launch-dashboard")

    assert response.status_code == 409


def test_launch_dashboard_blocks_viewer_role() -> None:
    project = create_awarded_project("Management Only Launch Job")

    def viewer_user(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000099"),
            email="viewer@ironhousecontracting.com",
            display_name="Viewer",
            role="viewer",
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = viewer_user
    try:
        response = client.get(f"/api/v1/projects/{project['id']}/launch-dashboard")
    finally:
        app.dependency_overrides[require_authenticated_user] = override_authenticated_user

    assert response.status_code == 403
