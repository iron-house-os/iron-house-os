from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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
