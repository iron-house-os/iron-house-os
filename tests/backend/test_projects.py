from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
IRON_HOUSE_TIME_ZONE = ZoneInfo("America/Vancouver")


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


def test_awarded_project_creation_generates_sequential_job_numbers() -> None:
    year = datetime.now(IRON_HOUSE_TIME_ZONE).year

    first = client.post("/api/v1/projects", json={"name": "First Award", "status": "awarded"})
    second = client.post("/api/v1/projects", json={"name": "Second Award", "status": "awarded"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["project_number"] == f"IH-{year}-001"
    assert second.json()["project_number"] == f"IH-{year}-002"


def test_transition_to_awarded_generates_job_number() -> None:
    year = datetime.now(IRON_HOUSE_TIME_ZONE).year
    project = client.post("/api/v1/projects", json={"name": "Tender Without Number"}).json()

    response = client.patch(f"/api/v1/projects/{project['id']}", json={"status": "awarded"})

    assert response.status_code == 200
    assert response.json()["status"] == "awarded"
    assert response.json()["project_number"] == f"IH-{year}-001"


def test_award_generation_skips_existing_numbers_and_preserves_explicit_number() -> None:
    year = datetime.now(IRON_HOUSE_TIME_ZONE).year
    explicit = client.post(
        "/api/v1/projects",
        json={"name": "Existing Award", "status": "awarded", "project_number": f"IH-{year}-009"},
    )
    generated = client.post("/api/v1/projects", json={"name": "Next Award", "status": "awarded"})

    assert explicit.status_code == 201
    assert explicit.json()["project_number"] == f"IH-{year}-009"
    assert generated.status_code == 201
    assert generated.json()["project_number"] == f"IH-{year}-010"


def test_award_generation_retries_a_unique_collision() -> None:
    year = datetime.now(IRON_HOUSE_TIME_ZONE).year
    duplicate = f"IH-{year}-001"
    available = f"IH-{year}-002"
    client.post(
        "/api/v1/projects",
        json={"name": "Existing Number", "status": "awarded", "project_number": duplicate},
    )

    with patch("app.services.projects._next_job_number", side_effect=[duplicate, available]):
        response = client.post("/api/v1/projects", json={"name": "Concurrent Award", "status": "awarded"})

    assert response.status_code == 201
    assert response.json()["project_number"] == available


def test_assigned_job_number_is_not_removed_or_replaced_by_project_update() -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Award With Custom Number", "status": "awarded", "project_number": "CLIENT-JOB-77"},
    ).json()

    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"project_number": None, "status": "construction"},
    )

    assert response.status_code == 200
    assert response.json()["project_number"] == "CLIENT-JOB-77"
    assert response.json()["status"] == "construction"


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
