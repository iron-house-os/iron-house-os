from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_supplier(name: str = "Pacific Pipe Supply", category: str = "pipe") -> dict:
    response = client.post(
        "/api/v1/suppliers",
        json={
            "name": name,
            "category": category,
            "service_area": "Lower Mainland",
            "website": "https://example.com",
            "notes": "Preferred supplier for Phase 2 CRM foundation.",
            "metadata": {"source": "test"},
            "contacts": [
                {
                    "first_name": "Sam",
                    "last_name": "Estimator",
                    "email": "sam@example.com",
                    "phone": "604-555-0100",
                    "role": "Estimator",
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_supplier_with_contact() -> None:
    supplier = create_supplier()

    assert supplier["name"] == "Pacific Pipe Supply"
    assert supplier["contacts"][0]["email"] == "sam@example.com"


def test_list_supplier_search_and_category_filter() -> None:
    create_supplier()
    create_supplier(name="Fraser Valley Aggregates", category="aggregates")

    search_response = client.get("/api/v1/suppliers?search=Pacific")
    category_response = client.get("/api/v1/suppliers?category=aggregates")

    assert search_response.status_code == 200
    assert search_response.json()["total"] == 1
    assert category_response.json()["items"][0]["name"] == "Fraser Valley Aggregates"


def test_read_supplier_detail_persists_across_requests() -> None:
    supplier = create_supplier()

    first_response = client.get(f"/api/v1/suppliers/{supplier['id']}")
    second_response = client.get(f"/api/v1/suppliers/{supplier['id']}")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["contacts"][0]["first_name"] == "Sam"


def test_update_supplier_profile() -> None:
    supplier = create_supplier()

    response = client.patch(
        f"/api/v1/suppliers/{supplier['id']}",
        json={"service_area": "Metro Vancouver", "metadata": {"tier": "preferred"}},
    )

    assert response.status_code == 200
    assert response.json()["service_area"] == "Metro Vancouver"
    assert response.json()["metadata"] == {"tier": "preferred"}


def test_replace_supplier_contacts() -> None:
    supplier = create_supplier()

    response = client.put(
        f"/api/v1/suppliers/{supplier['id']}/contacts",
        json=[
            {
                "first_name": "Avery",
                "last_name": "Coordinator",
                "email": "avery@example.com",
                "role": "Coordinator",
            }
        ],
    )
    detail_response = client.get(f"/api/v1/suppliers/{supplier['id']}")

    assert response.status_code == 200
    assert len(detail_response.json()["contacts"]) == 1
    assert detail_response.json()["contacts"][0]["first_name"] == "Avery"


def test_bulk_supplier_import_structure() -> None:
    response = client.post(
        "/api/v1/suppliers/bulk",
        json={
            "suppliers": [
                {"name": "Supplier A", "category": "pipe"},
                {"name": "Supplier B", "category": "traffic"},
            ]
        },
    )

    assert response.status_code == 201
    assert response.json()["total"] == 2


def test_missing_supplier_returns_404() -> None:
    response = client.get("/api/v1/suppliers/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
