from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_package() -> dict:
    response = client.post(
        "/api/v1/rfqs",
        json={
            "title": "Stormwater Pipe RFQ",
            "project_name": "King George Utility Upgrade",
            "scope_summary": "Supply pipe, fittings, and appurtenances for civil utility works.",
            "due_at": "2026-07-20T16:00:00Z",
            "supplier_category_targets": ["pipe", "civil materials"],
            "metadata": {"estimator": "Phase 2"},
        },
    )

    assert response.status_code == 201
    return response.json()


def add_suppliers(rfq_package_id: str) -> dict:
    response = client.put(
        f"/api/v1/rfqs/{rfq_package_id}/suppliers",
        json=[
            {
                "supplier_id": "supplier-001",
                "supplier_name": "Pacific Pipe Supply",
                "category": "pipe",
            },
            {
                "supplier_id": "supplier-002",
                "supplier_name": "Coastal Traffic Control",
                "category": "traffic control",
            },
        ],
    )
    assert response.status_code == 200
    return response.json()


def add_ready_documents(rfq_package_id: str) -> dict:
    response = client.put(
        f"/api/v1/rfqs/{rfq_package_id}/documents",
        json=[
            {
                "document_type": "drawing",
                "title": "C-101 Utility Plan",
                "required": True,
                "status": "attached",
                "storage_uri": "drive://projects/kg/C-101.pdf",
                "metadata": {"revision": "A"},
            },
            {
                "document_type": "specification",
                "title": "MMCD Supplemental Specifications",
                "required": True,
                "status": "attached",
                "storage_uri": "drive://projects/kg/specifications.pdf",
            },
        ],
    )
    assert response.status_code == 200
    return response.json()


def test_create_list_and_read_rfq_package() -> None:
    payload = create_package()

    assert payload["title"] == "Stormwater Pipe RFQ"
    assert payload["status"] == "draft"
    assert payload["supplier_category_targets"] == ["pipe", "civil materials"]

    listing = client.get("/api/v1/rfqs")
    detail = client.get(f"/api/v1/rfqs/{payload['id']}")

    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert detail.status_code == 200
    assert detail.json()["id"] == payload["id"]


def test_update_rfq_package_status() -> None:
    rfq_package = create_package()

    response = client.patch(
        f"/api/v1/rfqs/{rfq_package['id']}/status",
        json={"status": "assembling"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "assembling"


def test_supplier_selection_generates_category_specific_scopes() -> None:
    rfq_package = create_package()

    payload = add_suppliers(rfq_package["id"])

    assert len(payload["recipients"]) == 2
    pipe_recipient, traffic_recipient = payload["recipients"]
    assert pipe_recipient["status"] == "pending"
    assert traffic_recipient["status"] == "pending"
    assert any("pipe" in item.lower() for item in pipe_recipient["scope_items"])
    assert any("traffic control" in item.lower() for item in traffic_recipient["scope_items"])
    assert pipe_recipient["scope_items"] != traffic_recipient["scope_items"]


def test_custom_supplier_scope_is_preserved_until_forced_regeneration() -> None:
    rfq_package = create_package()
    response = client.put(
        f"/api/v1/rfqs/{rfq_package['id']}/suppliers",
        json=[
            {
                "supplier_id": "supplier-001",
                "supplier_name": "Pacific Pipe Supply",
                "category": "pipe",
                "scope_items": ["Price DR35 PVC pipe only."],
            }
        ],
    )
    assert response.status_code == 200

    preserved = client.post(
        f"/api/v1/rfqs/{rfq_package['id']}/supplier-scopes",
        json={"force": False},
    )
    regenerated = client.post(
        f"/api/v1/rfqs/{rfq_package['id']}/supplier-scopes",
        json={"force": True},
    )

    assert preserved.json()["recipients"][0]["scope_items"] == ["Price DR35 PVC pipe only."]
    assert regenerated.status_code == 200
    assert regenerated.json()["recipients"][0]["scope_items"] != [
        "Price DR35 PVC pipe only."
    ]


def test_document_checklist_requires_attachment_references() -> None:
    rfq_package = create_package()
    add_suppliers(rfq_package["id"])

    pending = client.put(
        f"/api/v1/rfqs/{rfq_package['id']}/documents",
        json=[
            {
                "document_type": "drawing",
                "title": "C-101 Utility Plan",
                "required": True,
            }
        ],
    )
    pending_readiness = client.get(
        f"/api/v1/rfqs/{rfq_package['id']}/readiness"
    )
    invalid = client.put(
        f"/api/v1/rfqs/{rfq_package['id']}/documents",
        json=[
            {
                "document_type": "drawing",
                "title": "C-101 Utility Plan",
                "required": True,
                "status": "attached",
            }
        ],
    )

    assert pending.status_code == 200
    assert pending.json()["documents"][0]["status"] == "pending"
    assert pending_readiness.json()["ready"] is False
    assert invalid.status_code == 422


def test_rfq_package_readiness_requires_scopes_and_attached_documents() -> None:
    rfq_package = create_package()
    add_suppliers(rfq_package["id"])
    add_ready_documents(rfq_package["id"])

    response = client.get(f"/api/v1/rfqs/{rfq_package['id']}/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["score"] == 100
    assert len(response.json()["items"]) == 4


def test_track_supplier_sent_replied_and_bounced_statuses() -> None:
    rfq_package = create_package()
    payload = add_suppliers(rfq_package["id"])
    first, second = payload["recipients"]

    sent = client.patch(
        f"/api/v1/rfqs/{rfq_package['id']}/suppliers/{first['id']}/status",
        json={"status": "sent", "note": "Issued manually at 09:00."},
    )
    replied = client.patch(
        f"/api/v1/rfqs/{rfq_package['id']}/suppliers/{first['id']}/status",
        json={"status": "replied", "note": "Quote received."},
    )
    bounced = client.patch(
        f"/api/v1/rfqs/{rfq_package['id']}/suppliers/{second['id']}/status",
        json={"status": "bounced", "note": "Mailbox rejected the address."},
    )

    assert sent.status_code == 200
    assert replied.json()["recipients"][0]["status"] == "replied"
    assert replied.json()["recipients"][0]["status_note"] == "Quote received."
    assert bounced.json()["recipients"][1]["status"] == "bounced"


def test_build_supplier_specific_rfq_drafts_without_sending() -> None:
    rfq_package = create_package()
    add_suppliers(rfq_package["id"])
    add_ready_documents(rfq_package["id"])

    response = client.post(f"/api/v1/rfqs/{rfq_package['id']}/build")

    payload = response.json()
    assert response.status_code == 200
    assert payload["ready"] is True
    assert payload["blockers"] == []
    assert len(payload["packages"]) == 2
    assert payload["packages"][0]["supplier_name"] == "Pacific Pipe Supply"
    assert "Pacific Pipe Supply" in payload["packages"][0]["subject"]
    assert "C-101 Utility Plan" in payload["packages"][0]["attachment_names"]
    assert payload["packages"][0]["scope_items"] != payload["packages"][1]["scope_items"]
    assert payload["packages"][0]["status"] == "pending"


def test_rfq_package_children_and_metadata_persist_across_requests() -> None:
    rfq_package = create_package()
    add_suppliers(rfq_package["id"])
    add_ready_documents(rfq_package["id"])

    first_response = client.get(f"/api/v1/rfqs/{rfq_package['id']}")
    second_response = client.get(f"/api/v1/rfqs/{rfq_package['id']}")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["recipients"][0]["scope_items"]
    assert second_response.json()["documents"][0]["storage_uri"].startswith("drive://")
