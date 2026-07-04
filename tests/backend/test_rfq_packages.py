from fastapi.testclient import TestClient

from app.main import app
from app.services.rfq_packages import rfq_package_store


client = TestClient(app)


def setup_function() -> None:
    rfq_package_store.reset()


def create_package() -> dict:
    response = client.post(
        "/api/v1/rfqs",
        json={
            "title": "Stormwater Pipe RFQ",
            "project_name": "King George Utility Upgrade",
            "scope_summary": "Supply pipe, fittings, and appurtenances for civil utility works.",
            "supplier_category_targets": ["pipe", "civil materials"],
            "metadata": {"estimator": "Phase 2"},
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_rfq_package() -> None:
    payload = create_package()

    assert payload["title"] == "Stormwater Pipe RFQ"
    assert payload["status"] == "draft"
    assert payload["supplier_category_targets"] == ["pipe", "civil materials"]


def test_list_rfq_packages() -> None:
    create_package()

    response = client.get("/api/v1/rfqs")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Stormwater Pipe RFQ"


def test_read_rfq_package_detail() -> None:
    rfq_package = create_package()

    response = client.get(f"/api/v1/rfqs/{rfq_package['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == rfq_package["id"]


def test_update_rfq_package_status() -> None:
    rfq_package = create_package()

    response = client.patch(
        f"/api/v1/rfqs/{rfq_package['id']}/status",
        json={"status": "assembling"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "assembling"


def test_select_rfq_package_suppliers() -> None:
    rfq_package = create_package()

    response = client.put(
        f"/api/v1/rfqs/{rfq_package['id']}/suppliers",
        json=[
            {
                "supplier_id": "supplier-001",
                "supplier_name": "Pacific Pipe Supply",
                "category": "pipe",
            },
            {
                "supplier_id": "supplier-002",
                "supplier_name": "Fraser Valley Aggregates",
                "category": "aggregates",
            },
        ],
    )

    assert response.status_code == 200
    assert len(response.json()["recipients"]) == 2
    assert response.json()["recipients"][0]["status"] == "selected"


def test_register_rfq_package_documents() -> None:
    rfq_package = create_package()

    response = client.put(
        f"/api/v1/rfqs/{rfq_package['id']}/documents",
        json=[
            {
                "document_type": "drawing",
                "title": "C-101 Utility Plan",
                "required": True,
                "metadata": {"revision": "A"},
            },
            {
                "document_type": "specification",
                "title": "MMCD Supplemental Specifications",
                "required": True,
            },
        ],
    )

    assert response.status_code == 200
    assert len(response.json()["documents"]) == 2
    assert response.json()["documents"][0]["status"] == "registered"


def test_rfq_package_readiness_summary() -> None:
    rfq_package = create_package()
    client.put(
        f"/api/v1/rfqs/{rfq_package['id']}/suppliers",
        json=[
            {
                "supplier_id": "supplier-001",
                "supplier_name": "Pacific Pipe Supply",
                "category": "pipe",
            }
        ],
    )
    client.put(
        f"/api/v1/rfqs/{rfq_package['id']}/documents",
        json=[
            {
                "document_type": "drawing",
                "title": "C-101 Utility Plan",
                "required": True,
            }
        ],
    )

    response = client.get(f"/api/v1/rfqs/{rfq_package['id']}/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["score"] == 100
    assert len(response.json()["items"]) == 3
