from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.services.auth import AuthenticatedUser


client = TestClient(app)


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000091"),
            email=f"{role}@ironhousecontracting.com",
            display_name=f"Test {role.replace('_', ' ').title()}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _project(name: str = "Completed Work Cost Test") -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": name, "project_number": "COST268" if name == "Completed Work Cost Test" else "COST269"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _completed_work(
    project_id: str,
    source_line_key: str = "01-common-excavation-2026-08-11",
) -> dict:
    response = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "completed_work",
            "project_id": project_id,
            "work_date": "2026-08-11",
            "title": "Common excavation - Tuesday, August 11, 2026",
            "details": {
                "source_import_key": "bowline-rawlison-2026-08-25",
                "source_line_key": source_line_key,
                "source_line_position": 1,
                "source_invoice_number": "BOW-2026-0811",
                "source_invoice_date": "2026-08-15",
                "source_drive_file_id": "1laUuqBbgcU5ck8rIz0Qd3N-Gd6I8U5ZS",
                "description": "Common excavation - Tuesday, August 11, 2026",
                "quantity": "12.5",
                "unit": "hour",
                "billable_rate": "220.00",
                "billable_amount": "2750.00",
                "record_date_basis": "source_work_date",
                "source_work_date": "2026-08-11",
                "cost_status": "internal_cost_unverified",
                "revenue_trace_only": True,
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cost_payload(record_id: str, key: str, amount: float = 612.50) -> dict:
    return {
        "completed_work_id": record_id,
        "idempotency_key": key,
        "cost_code": "02-100",
        "category": "equipment",
        "amount": amount,
        "entry_date": "2026-08-11",
        "vendor_name": None,
        "reference": "VERIFIED-EQUIPMENT-LOG-0811",
        "description": "Verified internal excavator cost from equipment log",
    }


def test_explicit_actual_cost_is_source_linked_idempotent_and_visible_in_summary() -> None:
    project = _project()
    record = _completed_work(project["id"])
    url = f"/api/v1/finance/projects/{project['id']}/completed-work-costs"

    before = client.get(url)
    assert before.status_code == 200, before.text
    assert before.json()["source_line_count"] == 1
    assert before.json()["unlinked_line_count"] == 1
    assert before.json()["linked_actual_cost_total"] == 0
    assert before.json()["lines"][0]["billable_amount"] == "2750.00"
    assert before.json()["lines"][0]["internal_cost_status"] == "internal_cost_unverified"

    imprecise = client.post(
        url,
        json=_cost_payload(
            record["id"],
            "00000000-0000-4000-8000-000000000000",
            amount=612.501,
        ),
    )
    assert imprecise.status_code == 422

    key = "11111111-1111-4111-8111-111111111111"
    created = client.post(url, json=_cost_payload(record["id"], key))
    assert created.status_code == 200, created.text
    result = created.json()
    assert result["created"] is True
    assert result["idempotent"] is False
    assert result["entry"]["entry_type"] == "actual"
    assert result["entry"]["status"] == "posted"
    assert result["entry"]["source_type"] == "completed_work_actual"
    assert result["entry"]["source_id"] == record["id"]
    assert result["entry"]["source_key"] == key
    assert result["entry"]["amount"] == 612.5
    assert result["entry"]["metadata_json"]["billable_values_not_used_as_cost"] is True

    repeated = client.post(url, json=_cost_payload(record["id"], key))
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["created"] is False
    assert repeated.json()["idempotent"] is True
    assert repeated.json()["entry"]["id"] == result["entry"]["id"]

    conflict = client.post(url, json=_cost_payload(record["id"], key, amount=2750))
    assert conflict.status_code == 409
    assert "different completed-work cost content" in conflict.json()["detail"]

    second_key = "22222222-2222-4222-8222-222222222222"
    second = client.post(url, json=_cost_payload(record["id"], second_key))
    assert second.status_code == 200, second.text
    assert second.json()["entry"]["id"] != result["entry"]["id"]

    ledger = client.get(url).json()
    assert ledger["linked_line_count"] == 1
    assert ledger["unlinked_line_count"] == 0
    assert ledger["linked_actual_cost_total"] == 1225
    assert len(ledger["lines"][0]["linked_entries"]) == 2
    assert "revenue evidence only" in ledger["warning"]
    assert "does not prove" in ledger["warning"]

    financials = client.get(f"/api/v1/finance/projects/{project['id']}").json()
    assert financials["actual"] == 1225
    assert financials["actual"] != float(ledger["lines"][0]["billable_amount"])


def test_idempotency_key_rejects_different_completed_work_in_same_project() -> None:
    project = _project()
    first_record = _completed_work(project["id"])
    second_record = _completed_work(
        project["id"],
        source_line_key="02-common-excavation-2026-08-12",
    )
    url = f"/api/v1/finance/projects/{project['id']}/completed-work-costs"
    key = "55555555-5555-4555-8555-555555555555"

    created = client.post(url, json=_cost_payload(first_record["id"], key))
    assert created.status_code == 200, created.text

    conflict = client.post(url, json=_cost_payload(second_record["id"], key))
    assert conflict.status_code == 409
    assert "different completed-work cost content" in conflict.json()["detail"]


def test_idempotency_key_is_independent_between_projects() -> None:
    first_project = _project()
    second_project = _project("Other Project")
    first_record = _completed_work(first_project["id"])
    second_record = _completed_work(second_project["id"])
    key = "66666666-6666-4666-8666-666666666666"

    first = client.post(
        f"/api/v1/finance/projects/{first_project['id']}/completed-work-costs",
        json=_cost_payload(first_record["id"], key),
    )
    second = client.post(
        f"/api/v1/finance/projects/{second_project['id']}/completed-work-costs",
        json=_cost_payload(second_record["id"], key),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["entry"]["id"] != second.json()["entry"]["id"]


def test_completed_work_cost_rejects_wrong_project_and_non_completed_work_source() -> None:
    project = _project()
    other_project = _project("Other Project")
    record = _completed_work(project["id"])
    other_url = f"/api/v1/finance/projects/{other_project['id']}/completed-work-costs"
    key = "33333333-3333-4333-8333-333333333333"

    wrong_project = client.post(other_url, json=_cost_payload(record["id"], key))
    assert wrong_project.status_code == 400
    assert "selected project" in wrong_project.json()["detail"]

    ordinary_record = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "journal",
            "project_id": project["id"],
            "work_date": "2026-08-11",
            "title": "Daily log",
            "details": {},
        },
    )
    assert ordinary_record.status_code == 201, ordinary_record.text
    project_url = f"/api/v1/finance/projects/{project['id']}/completed-work-costs"
    wrong_type = client.post(project_url, json=_cost_payload(ordinary_record.json()["id"], key))
    assert wrong_type.status_code == 400
    assert "not a completed-work record" in wrong_type.json()["detail"]


def test_completed_work_cost_ledger_and_create_are_management_only() -> None:
    project = _project()
    record = _completed_work(project["id"])
    url = f"/api/v1/finance/projects/{project['id']}/completed-work-costs"
    _authenticate_as("viewer")

    assert client.get(url).status_code == 403
    assert client.post(
        url,
        json=_cost_payload(record["id"], "44444444-4444-4444-8444-444444444444"),
    ).status_code == 403
