from copy import deepcopy
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.field_operations import FieldRecord
from app.services.auth import AuthenticatedUser
from conftest import TestingSessionLocal

client = TestClient(app)


def _project() -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Invoice package test project",
            "client_owner": "Verified customer reference",
            "project_number": "IH2026901",
            "project_address": "100 Verified Site Road",
            "status": "awarded",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _completed_work(
    project_id: str,
    *,
    source_import_key: str = "verified-source-2026-08-27",
    source_line_key: str = "line-01",
    description: str = "Verified excavation work",
    quantity: str = "2.5",
    rate: str = "220.00",
    amount: str = "550.00",
) -> dict:
    response = client.post(
        "/api/v1/field-operations/records",
        json={
            "record_type": "completed_work",
            "project_id": project_id,
            "work_date": "2026-08-20",
            "title": description,
            "details": {
                "source_import_key": source_import_key,
                "source_line_key": source_line_key,
                "source_line_position": 1,
                "source_invoice_number": "SOURCE-100",
                "source_invoice_date": "2026-08-21",
                "source_drive_file_id": "verified-drive-file-id",
                "description": description,
                "quantity": quantity,
                "unit": "hour",
                "billable_rate": rate,
                "billable_amount": amount,
                "record_date_basis": "source_work_date",
                "source_work_date": "2026-08-20",
                "cost_status": "internal_cost_unverified",
                "revenue_trace_only": True,
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _complete_project(project_id: str) -> None:
    checklist = client.get(f"/api/v1/projects/{project_id}/closeout-checklist")
    assert checklist.status_code == 200, checklist.text
    for item in checklist.json()["items"]:
        updated = client.patch(
            f"/api/v1/projects/{project_id}/closeout-checklist/{item['code']}",
            json={
                "completed": True,
                "evidence": f"Verified evidence for {item['code']}",
            },
        )
        assert updated.status_code == 200, updated.text
    completed = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "completed"},
    )
    assert completed.status_code == 200, completed.text


def _package_payload() -> dict:
    return {
        "source_import_key": "verified-source-2026-08-27",
        "invoice_number": "IH2026901-INV1",
        "customer_name": "Verified Customer Legal Name",
        "customer_address": "200 Verified Billing Avenue",
        "customer_phone": "604-555-0100",
        "invoice_date": "2026-08-27",
        "due_date": "2026-09-26",
        "terms": "Net 30",
        "gst_rate": "5.00",
    }


def test_completed_project_generates_traceable_source_exact_draft_once() -> None:
    project = _project()
    first_source = _completed_work(project["id"])
    second_source = _completed_work(
        project["id"],
        source_line_key="line-02",
        description="Verified trucking work",
        quantity="3",
        rate="150.00",
        amount="450.00",
    )

    before_completion = client.get(
        f"/api/v1/finance/projects/{project['id']}/invoice-package-readiness"
    )
    assert before_completion.status_code == 200
    assert before_completion.json()["ready"] is False
    assert "status must be completed" in before_completion.json()["blockers"][0]

    _complete_project(project["id"])
    readiness = client.get(
        f"/api/v1/finance/projects/{project['id']}/invoice-package-readiness"
    )
    assert readiness.status_code == 200, readiness.text
    body = readiness.json()
    assert body["ready"] is True
    assert body["closeout_status"] == "ready"
    assert body["customer_reference"] == "Verified customer reference"
    assert body["site_address"] == "100 Verified Site Road"
    assert len(body["groups"]) == 1
    assert body["groups"][0]["line_count"] == 2
    assert body["groups"][0]["subtotal"] == "1000.00"

    created = client.post(
        f"/api/v1/finance/projects/{project['id']}/invoice-package",
        json=_package_payload(),
    )
    assert created.status_code == 200, created.text
    result = created.json()
    invoice = result["invoice"]
    assert result["created"] is True
    assert result["idempotent"] is False
    assert invoice["status"] == "draft"
    assert invoice["project_name"] == project["name"]
    assert invoice["site_address"] == project["project_address"]
    assert invoice["subtotal"] == "1000.00"
    assert invoice["gst"] == "50.00"
    assert invoice["total"] == "1050.00"
    assert invoice["line_items"] == [
        {
            "description": "Verified excavation work",
            "quantity": "2.5",
            "unit": "hour",
            "unit_price": "220.00",
            "amount": "550.00",
        },
        {
            "description": "Verified trucking work",
            "quantity": "3",
            "unit": "hour",
            "unit_price": "150.00",
            "amount": "450.00",
        },
    ]
    assert invoice["source_import_key"] == "verified-source-2026-08-27"
    assert invoice["source_record_ids"] == [first_source["id"], second_source["id"]]
    assert invoice["source_package_key"].startswith("completed-work:")
    assert invoice["package_generated_by"] == "test-admin@ironhousecontracting.com"
    assert invoice["closeout_snapshot"]["status"] == "ready"
    assert len(invoice["closeout_snapshot"]["controls"]) == 10

    repeated = client.post(
        f"/api/v1/finance/projects/{project['id']}/invoice-package",
        json=_package_payload(),
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["invoice"]["id"] == invoice["id"]
    assert repeated.json()["created"] is False
    assert repeated.json()["idempotent"] is True

    conflict_payload = deepcopy(_package_payload())
    conflict_payload["invoice_number"] = "IH2026901-INV2"
    conflict = client.post(
        f"/api/v1/finance/projects/{project['id']}/invoice-package",
        json=conflict_payload,
    )
    assert conflict.status_code == 409
    assert "different invoice package" in conflict.json()["detail"]

    reopened = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "construction"},
    )
    assert reopened.status_code == 200
    replay_after_reopen = client.post(
        f"/api/v1/finance/projects/{project['id']}/invoice-package",
        json=_package_payload(),
    )
    assert replay_after_reopen.status_code == 200
    assert replay_after_reopen.json()["invoice"]["id"] == invoice["id"]
    assert replay_after_reopen.json()["idempotent"] is True


def test_source_groups_stay_separate_and_invalid_group_fails_closed() -> None:
    project = _project()
    valid = _completed_work(project["id"])
    invalid = _completed_work(
        project["id"],
        source_import_key="second-exact-source",
        source_line_key="second-01",
    )
    with TestingSessionLocal() as db:
        record = db.get(FieldRecord, UUID(invalid["id"]))
        assert record is not None
        record.details = {**record.details, "billable_amount": "551.00"}
        db.commit()
    _complete_project(project["id"])

    readiness = client.get(
        f"/api/v1/finance/projects/{project['id']}/invoice-package-readiness"
    ).json()
    assert readiness["ready"] is True
    assert [group["source_import_key"] for group in readiness["groups"]] == [
        "second-exact-source",
        "verified-source-2026-08-27",
    ]
    groups = {group["source_import_key"]: group for group in readiness["groups"]}
    assert groups["verified-source-2026-08-27"]["ready"] is True
    assert groups["verified-source-2026-08-27"]["lines"][0]["id"] == valid["id"]
    assert groups["second-exact-source"]["ready"] is False
    assert "does not equal" in groups["second-exact-source"]["blockers"][0]

    invalid_payload = _package_payload()
    invalid_payload["source_import_key"] = "second-exact-source"
    blocked = client.post(
        f"/api/v1/finance/projects/{project['id']}/invoice-package",
        json=invalid_payload,
    )
    assert blocked.status_code == 409
    assert "does not equal" in blocked.json()["detail"]


def test_invoice_package_endpoints_require_management() -> None:
    project = _project()

    def viewer(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000099"),
            email="viewer@example.com",
            display_name="Viewer",
            role="viewer",
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = viewer
    readiness = client.get(
        f"/api/v1/finance/projects/{project['id']}/invoice-package-readiness"
    )
    generate = client.post(
        f"/api/v1/finance/projects/{project['id']}/invoice-package",
        json=_package_payload(),
    )
    assert readiness.status_code == 403
    assert generate.status_code == 403
