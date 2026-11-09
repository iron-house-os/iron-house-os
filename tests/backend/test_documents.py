from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_rfq_package() -> dict:
    response = client.post("/api/v1/rfqs", json={"title": "Pipe Supply RFQ"})
    assert response.status_code == 201
    return response.json()


def create_document(category: str = "specification") -> dict:
    response = client.post(
        "/api/v1/documents",
        json={
            "title": "Project Specifications",
            "category": category,
            "status": "registered",
            "storage_uri": "drive://future/specs.pdf",
            "description": "Metadata-only registration.",
            "metadata": {"source": "manual"},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_document_metadata_only() -> None:
    document = create_document()

    assert document["title"] == "Project Specifications"
    assert document["category"] == "specification"
    assert document["storage_uri"] == "drive://future/specs.pdf"


def test_list_and_filter_documents() -> None:
    create_document("specification")
    create_document("permit")

    response = client.get("/api/v1/documents?category=permit")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["category"] == "permit"


def test_read_document_detail() -> None:
    document = create_document()

    response = client.get(f"/api/v1/documents/{document['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == document["id"]


def test_update_document_and_status() -> None:
    document = create_document()

    update_response = client.patch(
        f"/api/v1/documents/{document['id']}",
        json={"title": "Updated Specifications", "category": "addendum"},
    )
    status_response = client.patch(
        f"/api/v1/documents/{document['id']}/status",
        json={"status": "active"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Specifications"
    assert status_response.json()["status"] == "active"


def test_drawing_metadata_registration() -> None:
    response = client.post(
        "/api/v1/documents",
        json={
            "title": "C-101 Utility Plan",
            "category": "drawing",
            "drawing": {
                "sheet_number": "C-101",
                "title": "Utility Plan",
                "discipline": "civil",
                "revision": "A",
                "issue_date": "2026-07-03",
                "storage_uri": "drive://future/drawings/c-101.pdf",
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["drawing"]["sheet_number"] == "C-101"
    assert response.json()["drawing"]["discipline"] == "civil"
    assert response.json()["storage_uri"] == "drive://future/drawings/c-101.pdf"


def test_rfq_linked_document() -> None:
    rfq_package = create_rfq_package()

    response = client.post(
        "/api/v1/documents",
        json={
            "title": "RFQ Attachment List",
            "category": "quote_request",
            "rfq_package_id": rfq_package["id"],
        },
    )
    list_response = client.get(f"/api/v1/documents?rfq_package_id={rfq_package['id']}")

    assert response.status_code == 201
    assert response.json()["rfq_package_id"] == rfq_package["id"]
    assert list_response.json()["total"] == 1


def test_missing_document_returns_404() -> None:
    response = client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
