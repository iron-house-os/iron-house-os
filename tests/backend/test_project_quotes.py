from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _project(name: str) -> dict:
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def _quote(project_id: str, **overrides: object) -> dict:
    payload = {
        "project_id": project_id,
        "supplier_name": "EMCO",
        "quote_reference": "Q-PIPE-001",
        "line_item_code": "PIPE-001",
        "line_item_description": "PVC storm pipe",
        "scope": "Supply PVC storm pipe",
        "scope_type": "material",
        "status": "received",
        "amount": 12500,
        "is_qualified": True,
        "qualification_notes": [],
        "is_selected": False,
        "exclusions": [],
    }
    payload.update(overrides)
    response = client.post("/api/v1/quotes", json=payload)
    assert response.status_code == 201
    return response.json()


def test_project_quote_register_creates_lists_and_updates_quotes() -> None:
    project = _project("King George Utility Upgrade")
    created = _quote(project["id"])

    listing = client.get("/api/v1/quotes", params={"project_id": project["id"]})
    updated = client.patch(
        f"/api/v1/quotes/{created['id']}",
        json={
            "is_selected": True,
            "selection_reason": "Confirmed delivery and complete scope",
            "qualification_notes": ["  Lead time confirmed  ", ""],
        },
    )

    assert listing.status_code == 200
    assert listing.json()["items"][0]["project_id"] == project["id"]
    assert listing.json()["items"][0]["supplier_name"] == "EMCO"
    assert updated.status_code == 200
    assert updated.json()["is_selected"] is True
    assert updated.json()["selection_reason"] == "Confirmed delivery and complete scope"
    assert updated.json()["qualification_notes"] == ["Lead time confirmed"]


def test_project_quote_register_never_mixes_projects() -> None:
    first = _project("First project")
    second = _project("Second project")
    first_quote = _quote(first["id"], supplier_name="First Supplier")
    _quote(second["id"], supplier_name="Second Supplier")

    response = client.get("/api/v1/quotes", params={"project_id": first["id"]})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == first_quote["id"]


def test_quote_rejects_cross_project_rfq_package_link() -> None:
    first = _project("First linked project")
    second = _project("Second linked project")
    package = client.post(
        "/api/v1/rfqs",
        json={
            "project_id": second["id"],
            "project_name": second["name"],
            "title": "Second project RFQ",
        },
    ).json()

    response = client.post(
        "/api/v1/quotes",
        json={
            "project_id": first["id"],
            "rfq_package_id": package["id"],
            "supplier_name": "Wrong project supplier",
            "scope": "Pipe",
            "amount": 1000,
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "RFQ package does not belong to the selected project"
    )
