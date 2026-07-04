from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def tender_payload() -> dict:
    return {
        "title": "Newton Watermain Replacement",
        "tender_number": "T-2026-500",
        "source": "manual",
        "source_url": "https://example.com/tenders/T-2026-500",
        "owner": "City of Surrey",
        "municipality": "Surrey",
        "closing_date": "2026-08-15",
        "site_meeting_date": "2026-07-20",
        "question_deadline": "2026-08-01",
        "project_address": "72 Avenue and 152 Street",
        "description": "Watermain, storm sewer, concrete restoration, and traffic control.",
        "status": "new",
        "estimated_value": 2400000,
        "metadata": {"source_note": "manual test intake"},
    }


def test_tender_crud() -> None:
    create_response = client.post("/api/v1/tenders", json=tender_payload())
    assert create_response.status_code == 201
    tender = create_response.json()
    assert tender["title"] == "Newton Watermain Replacement"
    assert tender["status"] == "new"

    list_response = client.get("/api/v1/tenders")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = client.get(f"/api/v1/tenders/{tender['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["tender_number"] == "T-2026-500"

    update_response = client.patch(
        f"/api/v1/tenders/{tender['id']}",
        json={"status": "reviewing", "municipality": "Burnaby"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "reviewing"
    assert update_response.json()["municipality"] == "Burnaby"


def test_tender_intake_creates_linked_records() -> None:
    response = client.post(
        "/api/v1/tenders/intake",
        json={
            **tender_payload(),
            "documents": [
                {
                    "title": "C-101 Utility Plan",
                    "category": "drawing",
                    "storage_uri": "drive://future/c-101.pdf",
                },
                {
                    "title": "Geotechnical Report",
                    "category": "geotechnical",
                },
            ],
        },
    )

    assert response.status_code == 201
    intake = response.json()
    assert intake["tender"]["id"]
    assert intake["project"]["id"] == intake["tender"]["project_id"]
    assert intake["rfq_package"]["id"] == intake["tender"]["rfq_package_id"]
    assert intake["rfq_package"]["project_id"] == intake["project"]["id"]
    assert len(intake["documents"]) == 2
    assert {document["tender_id"] for document in intake["documents"]} == {
        intake["tender"]["id"]
    }


def test_tender_intake_registers_documents_and_rfq_package_documents() -> None:
    response = client.post(
        "/api/v1/tenders/intake",
        json={
            **tender_payload(),
            "tender_number": "T-2026-501",
            "documents": [
                {"title": "Specifications", "category": "specification"},
                {"title": "Traffic Management Requirements", "category": "traffic_control"},
            ],
        },
    )
    intake = response.json()

    documents_response = client.get(
        f"/api/v1/documents?tender_id={intake['tender']['id']}"
    )
    rfq_response = client.get(f"/api/v1/rfqs/{intake['rfq_package']['id']}")

    assert documents_response.status_code == 200
    assert documents_response.json()["total"] == 2
    assert rfq_response.status_code == 200
    assert len(rfq_response.json()["documents"]) == 2


def test_supplier_category_suggestions_from_keywords_and_documents() -> None:
    response = client.post(
        "/api/v1/tenders/intake",
        json={
            **tender_payload(),
            "tender_number": "T-2026-502",
            "description": "Paving, streetlight upgrades, and sewer main replacement.",
            "documents": [{"title": "Environmental Requirements", "category": "environmental"}],
        },
    )

    assert response.status_code == 201
    suggestions = response.json()["suggested_supplier_categories"]
    assert "environmental" in suggestions
    assert "electrical" in suggestions
    assert "paving" in suggestions
    assert "pipe and fittings" in suggestions


def test_missing_tender_returns_404() -> None:
    response = client.get("/api/v1/tenders/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
