from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_equipment_create_list_and_update() -> None:
    created = client.post(
        "/api/v1/equipment",
        json={
            "name": "Rental 20 t excavator",
            "equipment_type": "Excavator",
            "identifier": "RENTAL-EX-20T",
            "status": "available",
            "hourly_rate": 195,
        },
    )
    assert created.status_code == 201
    equipment_id = created.json()["id"]

    listed = client.get("/api/v1/equipment?status=available")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["name"] == "Rental 20 t excavator"

    updated = client.patch(
        f"/api/v1/equipment/{equipment_id}",
        json={"status": "reserved", "hourly_rate": 205},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "reserved"
    assert updated.json()["hourly_rate"] == 205
