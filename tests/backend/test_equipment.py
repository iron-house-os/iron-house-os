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
            "safety_procedure_codes": ["swp-003", "SWP-008", "swp-003"],
        },
    )
    assert created.status_code == 201
    equipment_id = created.json()["id"]
    assert created.json()["assigned_employee_id"] is None
    assert created.json()["safety_procedure_codes"] == ["SWP-003", "SWP-008"]

    read = client.get(f"/api/v1/equipment/{equipment_id}")
    assert read.status_code == 200
    assert read.json()["identifier"] == "RENTAL-EX-20T"

    listed = client.get("/api/v1/equipment?status=available")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["name"] == "Rental 20 t excavator"

    employee = client.post(
        "/api/v1/field-operations/employees",
        json={
            "first_name": "Assigned",
            "last_name": "Operator",
            "email": "assigned.operator@ironhousecontracting.com",
            "portal_role": "employee",
        },
    )
    assert employee.status_code == 201

    updated = client.patch(
        f"/api/v1/equipment/{equipment_id}",
        json={"status": "reserved", "hourly_rate": 205, "assigned_employee_id": employee.json()["id"], "safety_procedure_codes": ["SWP-001"]},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "reserved"
    assert updated.json()["hourly_rate"] == 205
    assert updated.json()["assigned_employee_id"] == employee.json()["id"]
    assert updated.json()["safety_procedure_codes"] == ["SWP-001"]

    rejected = client.patch(
        f"/api/v1/equipment/{equipment_id}",
        json={"safety_procedure_codes": ["SWP-DRAFT"]},
    )
    assert rejected.status_code == 422
