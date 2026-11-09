from uuid import UUID

import pytest

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.bid import Bid
from app.models.customer_quote import CustomerQuote
from app.services.auth import AuthenticatedUser
from conftest import TestingSessionLocal

client = TestClient(app)


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email=f"{role}@ironhousecontracting.com",
            display_name=f"Test {role}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _payload() -> dict:
    return {
        "project_name": "Smith drainage repair",
        "customer_name": "Alex Smith",
        "customer_email": "alex@example.com",
        "customer_phone": "250-555-0100",
        "site_address": "100 Main Street, Chilliwack BC",
        "scope_summary": "Replace failed storm service and restore the driveway.",
        "line_items": [
            {"description": "Excavation and pipe replacement", "quantity": "1", "unit": "LS", "unit_price": "10000.00"},
            {"description": "Driveway restoration", "quantity": "2", "unit": "day", "unit_price": "1000.00"},
        ],
        "assumptions": ["Normal weekday access"],
        "exclusions": ["Contaminated soil disposal"],
        "gst_rate": "5.00",
        "quote_date": "2026-08-21",
        "valid_until": "2026-09-20",
        "notes": "Prepared from customer phone call.",
    }


def _create_quote() -> dict:
    response = client.post("/api/v1/customer-quotes", json=_payload())
    assert response.status_code == 201, response.text
    return response.json()


def _estimate_workspace(
    *,
    customer_name: str | None = "Bennett Strata",
    direct_cost: float = 10000,
    include_summary: bool = True,
) -> tuple[dict, dict]:
    project = client.post(
        "/api/v1/projects",
        json={
            "name": "Bennett Road concrete repair",
            "client_owner": customer_name,
            "project_address": "Bennett Road, Richmond, BC",
            "status": "opportunity",
        },
    ).json()
    estimate = {
        "project_name": "Bennett Road concrete repair",
        "line_items": [
            {
                "description": "Concrete pull and pour",
                "quantity": 1,
                "unit": "LS",
                "direct_unit_cost": direct_cost,
            }
        ],
        "markup": {"profit_percent": 20},
        "assumptions": ["Normal weekday access"],
        "exclusions": ["Hazardous material removal"],
    }
    summary = client.post("/api/v1/estimates/summary", json=estimate).json()
    workspace = client.post(
        "/api/v1/estimates/workspace",
        json={
            "project_id": project["id"],
            "status": "draft",
            "estimate": estimate,
            "summary": summary if include_summary else None,
        },
    ).json()
    return project, workspace


def test_verbal_quote_creates_a_durable_opportunity_without_job_number() -> None:
    created = _create_quote()

    assert created["quote_number"].startswith("Q-2026-")
    assert created["status"] == "draft"
    assert created["subtotal"] == "12000.00"
    assert created["gst"] == "600.00"
    assert created["total"] == "12600.00"
    assert created["job_number"] is None

    project = client.get(f"/api/v1/projects/{created['project_id']}")
    assert project.status_code == 200
    assert project.json()["status"] == "opportunity"
    assert project.json()["project_number"] is None
    assert project.json()["client_owner"] == "Alex Smith"

    listed = client.get("/api/v1/customer-quotes")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == created["id"]

    pdf = client.get(f"/api/v1/customer-quotes/{created['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_saved_estimate_creates_a_provenance_linked_draft_quote_without_reentry() -> None:
    project, workspace = _estimate_workspace()

    response = client.post(f"/api/v1/customer-quotes/from-estimate/{workspace['id']}")

    assert response.status_code == 201, response.text
    created = response.json()
    assert created["project_id"] == project["id"]
    assert created["source_estimate_workspace_id"] == workspace["id"]
    assert created["project_name"] == "Bennett Road concrete repair"
    assert created["customer_name"] == "Bennett Strata"
    assert created["site_address"] == "Bennett Road, Richmond, BC"
    assert created["scope_summary"] == "Bennett Road concrete repair — Concrete pull and pour"
    assert created["line_items"] == [
        {
            "description": "Bennett Road concrete repair",
            "quantity": "1",
            "unit": "LS",
            "unit_price": "12000.00",
            "amount": "12000.00",
        }
    ]
    assert created["assumptions"] == ["Normal weekday access"]
    assert created["exclusions"] == ["Hazardous material removal"]
    assert created["subtotal"] == "12000.00"
    assert created["gst"] == "600.00"
    assert created["total"] == "12600.00"
    assert created["status"] == "draft"
    assert created["issue_status"] == "draft"
    assert created["job_number"] is None

    with TestingSessionLocal() as db:
        quote = db.get(CustomerQuote, UUID(created["id"]))
        assert quote is not None
        assert quote.source_estimate_hash is not None
        snapshot = quote.source_estimate_snapshot_json
        assert snapshot["workspace_id"] == workspace["id"]
        assert snapshot["project_id"] == project["id"]
        assert snapshot["bid_json"]["summary"]["final_price"] == 12000.0

    edited = client.patch(
        f"/api/v1/customer-quotes/{created['id']}",
        json={"expected_revision": 1, "scope_summary": "Customer-facing scope wording"},
    )
    assert edited.status_code == 200
    with TestingSessionLocal() as db:
        quote = db.get(CustomerQuote, UUID(created["id"]))
        assert quote is not None
        assert quote.source_estimate_snapshot_json == snapshot


def test_estimate_quote_conversion_is_idempotent_across_identical_workspaces() -> None:
    project, first_workspace = _estimate_workspace()
    first = client.post(
        f"/api/v1/customer-quotes/from-estimate/{first_workspace['id']}"
    ).json()

    exact_retry = client.post(
        f"/api/v1/customer-quotes/from-estimate/{first_workspace['id']}"
    )
    assert exact_retry.status_code == 201
    assert exact_retry.json()["id"] == first["id"]

    duplicate_workspace = client.post(
        "/api/v1/estimates/workspace",
        json={
            "project_id": project["id"],
            "status": first_workspace["status"],
            "estimate": first_workspace["estimate"]["estimate"],
            "summary": first_workspace["estimate"]["summary"],
        },
    ).json()
    content_retry = client.post(
        f"/api/v1/customer-quotes/from-estimate/{duplicate_workspace['id']}"
    )
    assert content_retry.status_code == 201
    assert content_retry.json()["id"] == first["id"]
    assert content_retry.json()["source_estimate_workspace_id"] == first_workspace["id"]

    quotes = client.get("/api/v1/customer-quotes").json()
    assert quotes["total"] == 1

    with TestingSessionLocal() as db:
        workspace = db.get(Bid, UUID(first_workspace["id"]))
        assert workspace is not None
        changed = dict(workspace.bid_json)
        changed_summary = dict(changed["summary"])
        changed_summary["final_price"] = 13000
        changed["summary"] = changed_summary
        workspace.bid_json = changed
        db.commit()
    changed_source = client.post(
        f"/api/v1/customer-quotes/from-estimate/{first_workspace['id']}"
    )
    assert changed_source.status_code == 409
    assert "changed after" in changed_source.json()["error"]["message"].lower()


def test_estimate_quote_conversion_rejects_incomplete_or_ineligible_sources() -> None:
    _, no_customer = _estimate_workspace(customer_name=None)
    missing_customer = client.post(
        f"/api/v1/customer-quotes/from-estimate/{no_customer['id']}"
    )
    assert missing_customer.status_code == 409
    assert "customer name" in missing_customer.json()["error"]["message"].lower()

    _, no_summary = _estimate_workspace(include_summary=False)
    missing_summary = client.post(
        f"/api/v1/customer-quotes/from-estimate/{no_summary['id']}"
    )
    assert missing_summary.status_code == 409
    assert "calculate and save" in missing_summary.json()["error"]["message"].lower()

    _, zero_price = _estimate_workspace(direct_cost=0)
    invalid_price = client.post(
        f"/api/v1/customer-quotes/from-estimate/{zero_price['id']}"
    )
    assert invalid_price.status_code == 409
    assert "greater than zero" in invalid_price.json()["error"]["message"].lower()

    _, invalid_summary = _estimate_workspace()
    with TestingSessionLocal() as db:
        workspace = db.get(Bid, UUID(invalid_summary["id"]))
        assert workspace is not None
        malformed = dict(workspace.bid_json)
        malformed["summary"] = {"project_name": "Incomplete summary"}
        workspace.bid_json = malformed
        db.commit()
    invalid = client.post(
        f"/api/v1/customer-quotes/from-estimate/{invalid_summary['id']}"
    )
    assert invalid.status_code == 409
    assert "summary is invalid" in invalid.json()["error"]["message"].lower()

    project, archived_workspace = _estimate_workspace()
    archived = client.post(f"/api/v1/projects/{project['id']}/archive")
    assert archived.status_code == 200
    blocked = client.post(
        f"/api/v1/customer-quotes/from-estimate/{archived_workspace['id']}"
    )
    assert blocked.status_code == 409
    assert "archived" in blocked.json()["error"]["message"].lower()


def test_sent_quote_remains_non_binding_and_stale_edits_are_rejected() -> None:
    created = _create_quote()
    ready = client.post(
        f"/api/v1/customer-quotes/{created['id']}/issue-status",
        json={"expected_revision": 1, "status": "ready_for_review"},
    ).json()
    approved = client.post(
        f"/api/v1/customer-quotes/{created['id']}/issue-status",
        json={"expected_revision": ready["record_revision"], "status": "approved_for_issue"},
    ).json()
    sent = client.post(
        f"/api/v1/customer-quotes/{created['id']}/issue-status",
        json={
            "expected_revision": approved["record_revision"],
            "status": "issued",
            "issuance_method": "Email",
            "issuance_reference": "Customer email 2026-08-21",
        },
    )

    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"
    assert sent.json()["issue_status"] == "issued"
    assert sent.json()["record_revision"] == 4
    assert sent.json()["job_number"] is None

    stale = client.patch(
        f"/api/v1/customer-quotes/{created['id']}",
        json={"expected_revision": 1, "scope_summary": "Stale overwrite"},
    )
    assert stale.status_code == 409
    assert client.get(f"/api/v1/projects/{created['project_id']}").json()["status"] == "opportunity"


def test_unapproved_quote_cannot_be_issued_and_approved_snapshot_is_immutable() -> None:
    created = _create_quote()
    blocked = client.post(
        f"/api/v1/customer-quotes/{created['id']}/issue-status",
        json={
            "expected_revision": 1,
            "status": "issued",
            "issuance_method": "Email",
            "issuance_reference": "Not approved",
        },
    )
    assert blocked.status_code == 409

    ready = client.post(
        f"/api/v1/customer-quotes/{created['id']}/issue-status",
        json={"expected_revision": 1, "status": "ready_for_review"},
    ).json()
    approved = client.post(
        f"/api/v1/customer-quotes/{created['id']}/issue-status",
        json={"expected_revision": ready["record_revision"], "status": "approved_for_issue"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["approved_revision"] == 2
    assert approved.json()["approved_by"] == "test-admin@ironhousecontracting.com"

    edit = client.patch(
        f"/api/v1/customer-quotes/{created['id']}",
        json={"expected_revision": approved.json()["record_revision"], "scope_summary": "Changed after approval"},
    )
    assert edit.status_code == 409

    documents = client.get(f"/api/v1/documents?project_id={created['project_id']}")
    assert documents.status_code == 200
    linked = [item for item in documents.json()["items"] if item["metadata"].get("customer_quote_id") == created["id"]]
    assert len(linked) == 1


def test_estimator_can_submit_for_review_but_cannot_approve() -> None:
    _authenticate_as("estimator")
    created = _create_quote()
    ready = client.post(
        f"/api/v1/customer-quotes/{created['id']}/issue-status",
        json={"expected_revision": 1, "status": "ready_for_review"},
    )
    assert ready.status_code == 200
    denied = client.post(
        f"/api/v1/customer-quotes/{created['id']}/issue-status",
        json={"expected_revision": 2, "status": "approved_for_issue"},
    )
    assert denied.status_code == 403


def test_quote_date_cannot_be_cleared_on_update() -> None:
    created = _create_quote()

    rejected = client.patch(
        f"/api/v1/customer-quotes/{created['id']}",
        json={"expected_revision": 1, "quote_date": None},
    )

    assert rejected.status_code == 422
    unchanged = client.get(f"/api/v1/customer-quotes/{created['id']}").json()
    assert unchanged["quote_date"] == "2026-08-21"
    assert unchanged["record_revision"] == 1


def test_management_acceptance_atomically_awards_project_and_is_idempotent() -> None:
    created = _create_quote()
    acceptance = {
        "expected_revision": 1,
        "acceptance_reference": "Customer email received 2026-08-21",
        "acceptance_note": "Proceed at quoted scope and value.",
    }

    accepted = client.post(f"/api/v1/customer-quotes/{created['id']}/accept", json=acceptance)

    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["status"] == "accepted"
    assert body["record_revision"] == 2
    assert body["job_number"].startswith("IH2026")
    assert body["accepted_by"] == "test-admin@ironhousecontracting.com"

    project = client.get(f"/api/v1/projects/{created['project_id']}").json()
    assert project["status"] == "awarded"
    assert project["project_number"] == body["job_number"]
    assert project["contract_value"] == 12600.0
    baseline = project["metadata"]["award_pricing_baseline"]
    assert baseline["source_quote_id"] == created["id"]
    assert baseline["source_quote_number"] == created["quote_number"]
    assert baseline["pricing_subtotal"] == "12000.00"
    assert baseline["basis"] == "accepted_customer_quote_price"
    assert baseline["cost_budget_status"] == "needs_cost_allocation"
    assert len(baseline["lines"]) == 2
    assert all(line["cost_budget_amount"] is None for line in baseline["lines"])
    procurement = project["metadata"]["procurement_plan"]
    assert procurement["status"] == "draft"
    assert procurement["automatic_commitment"] is False
    assert all(item["vendor_id"] is None and item["po_number"] is None for item in procurement["requirements"])
    launch = client.get(f"/api/v1/projects/{created['project_id']}/launch-dashboard")
    assert launch.status_code == 200
    assert launch.json()["award_baseline_source"] == created["quote_number"]
    assert launch.json()["award_pricing_subtotal"] == 12000.0
    assert launch.json()["award_cost_budget_status"] == "needs_cost_allocation"
    assert launch.json()["uncoded_award_line_count"] == 2
    assert launch.json()["procurement_requirement_count"] == 1
    assert launch.json()["procurement_plan_status"] == "draft"

    checklist = client.get(f"/api/v1/projects/{created['project_id']}/start-checklist")
    assert checklist.status_code == 200
    assert checklist.json()["total_count"] == 10

    repeated = client.post(f"/api/v1/customer-quotes/{created['id']}/accept", json=acceptance)
    assert repeated.status_code == 200
    assert repeated.json()["job_number"] == body["job_number"]
    assert repeated.json()["record_revision"] == 2
    repeated_project = client.get(f"/api/v1/projects/{created['project_id']}").json()
    assert repeated_project["metadata"]["award_pricing_baseline"]["created_at"] == baseline["created_at"]
    assert repeated_project["metadata"]["procurement_plan"]["requirements"] == procurement["requirements"]


def test_estimator_can_prepare_but_cannot_accept_customer_quote() -> None:
    _authenticate_as("estimator")
    created = _create_quote()

    denied = client.post(
        f"/api/v1/customer-quotes/{created['id']}/accept",
        json={"expected_revision": 1, "acceptance_reference": "Must be management controlled"},
    )

    assert denied.status_code == 403
    assert client.get(f"/api/v1/projects/{created['project_id']}").json()["status"] == "opportunity"


def test_closed_quote_requires_an_editable_revision_before_reopening() -> None:
    created = _create_quote()
    declined = client.post(
        f"/api/v1/customer-quotes/{created['id']}/status",
        json={"expected_revision": 1, "status": "declined", "note": "Customer declined."},
    ).json()

    blocked = client.post(
        f"/api/v1/customer-quotes/{created['id']}/status",
        json={"expected_revision": 2, "status": "sent"},
    )
    assert blocked.status_code == 409

    revised = client.patch(
        f"/api/v1/customer-quotes/{created['id']}",
        json={
            "expected_revision": declined["record_revision"],
            "scope_summary": "Revised scope requested by the customer.",
        },
    )
    assert revised.status_code == 200
    assert revised.json()["status"] == "draft"
    assert revised.json()["record_revision"] == 3


def test_viewer_cannot_read_customer_quote_register() -> None:
    _authenticate_as("viewer")
    response = client.get("/api/v1/customer-quotes")
    assert response.status_code == 403


@pytest.mark.parametrize("project_status", ["awarded", "construction", "completed", "archived"])
def test_draft_edits_do_not_overwrite_awarded_project(project_status: str) -> None:
    original = _create_quote()
    accepted = client.post(
        f"/api/v1/customer-quotes/{original['id']}/accept",
        json={"expected_revision": 1, "acceptance_reference": "Signed contract"},
    )
    assert accepted.status_code == 200
    payload = {**_payload(), "project_id": original["project_id"]}
    draft = client.post("/api/v1/customer-quotes", json=payload).json()
    with TestingSessionLocal() as db:
        from app.models.project import Project
        project = db.get(Project, UUID(original["project_id"]))
        project.status = project_status
        db.commit()
    before = client.get(f"/api/v1/projects/{original['project_id']}").json()

    updated = client.patch(
        f"/api/v1/customer-quotes/{draft['id']}",
        json={
            "expected_revision": 1,
            "project_name": "Unapproved rename",
            "customer_name": "Different customer",
            "site_address": "Different address",
            "scope_summary": "Unaccepted extra scope",
            "line_items": [{"description": "Extra work", "quantity": "1", "unit": "LS", "unit_price": "999.00"}],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["total"] == "1048.95"
    assert client.get(f"/api/v1/projects/{original['project_id']}").json() == before
    with TestingSessionLocal() as db:
        from app.models.project import Project
        project = db.get(Project, UUID(original["project_id"]))
        assert project.description == _payload()["scope_summary"]


@pytest.mark.parametrize("closed_status", ["declined", "expired"])
@pytest.mark.parametrize("issue_status", ["approved_for_issue", "issued"])
def test_closed_approved_quote_creates_separate_draft_preserving_evidence(
    closed_status: str, issue_status: str,
) -> None:
    original = _create_quote()
    ready = client.post(
        f"/api/v1/customer-quotes/{original['id']}/issue-status",
        json={"expected_revision": 1, "status": "ready_for_review"},
    ).json()
    approved = client.post(
        f"/api/v1/customer-quotes/{original['id']}/issue-status",
        json={"expected_revision": ready["record_revision"], "status": "approved_for_issue"},
    ).json()
    current = approved
    if issue_status == "issued":
        current = client.post(
            f"/api/v1/customer-quotes/{original['id']}/issue-status",
            json={
                "expected_revision": approved["record_revision"], "status": "issued",
                "issuance_method": "Email", "issuance_reference": "Original delivery",
            },
        ).json()
    closed = client.post(
        f"/api/v1/customer-quotes/{original['id']}/status",
        json={"expected_revision": current["record_revision"], "status": closed_status},
    ).json()
    with TestingSessionLocal() as db:
        snapshot = db.get(CustomerQuote, UUID(original["id"])).approved_snapshot_json

    replacement = client.post(
        f"/api/v1/customer-quotes/{original['id']}/revisions",
        json={
            **_payload(), "expected_revision": closed["record_revision"],
            "scope_summary": "Replacement scope", "project_id": None,
        },
    )
    assert replacement.status_code == 201, replacement.text
    draft = replacement.json()
    assert draft["id"] != original["id"]
    assert draft["quote_number"] != original["quote_number"]
    assert draft["project_id"] == original["project_id"]
    assert draft["scope_summary"] == "Replacement scope"
    assert draft["status"] == draft["issue_status"] == "draft"
    assert draft["approved_at"] is None
    assert draft["issued_at"] is None
    assert original["quote_number"] in draft["notes"]
    assert client.get(f"/api/v1/customer-quotes/{original['id']}").json() == closed
    with TestingSessionLocal() as db:
        assert db.get(CustomerQuote, UUID(original["id"])).approved_snapshot_json == snapshot
    edited = client.patch(
        f"/api/v1/customer-quotes/{draft['id']}",
        json={"expected_revision": 1, "scope_summary": "Editable replacement"},
    )
    assert edited.status_code == 200
    direct_edit = client.patch(
        f"/api/v1/customer-quotes/{original['id']}",
        json={"expected_revision": closed["record_revision"], "scope_summary": "Overwrite original"},
    )
    assert direct_edit.status_code == 409
    issue_without_review = client.post(
        f"/api/v1/customer-quotes/{draft['id']}/issue-status",
        json={"expected_revision": 2, "status": "issued", "issuance_method": "Email", "issuance_reference": "No"},
    )
    assert issue_without_review.status_code == 409


def test_quote_revision_rejects_stale_or_nonclosed_source() -> None:
    original = _create_quote()
    url = f"/api/v1/customer-quotes/{original['id']}/revisions"
    assert client.post(url, json={**_payload(), "expected_revision": 1}).status_code == 409
    closed = client.post(
        f"/api/v1/customer-quotes/{original['id']}/status",
        json={"expected_revision": 1, "status": "declined"},
    ).json()
    assert closed["record_revision"] == 2
    assert client.post(url, json={**_payload(), "expected_revision": 1}).status_code == 409


def test_replacement_notes_reject_overflow_without_truncating_or_creating_a_quote() -> None:
    original = _create_quote()
    closed = client.post(
        f"/api/v1/customer-quotes/{original['id']}/status",
        json={"expected_revision": 1, "status": "declined"},
    ).json()
    before = client.get("/api/v1/customer-quotes").json()
    response = client.post(
        f"/api/v1/customer-quotes/{original['id']}/revisions",
        json={**_payload(), "expected_revision": closed["record_revision"], "notes": "N" * 10_000},
    )
    assert response.status_code == 422, response.text
    assert "No notes have been saved or truncated" in response.json()["error"]["message"]
    assert client.get("/api/v1/customer-quotes").json() == before
    assert client.get(f"/api/v1/customer-quotes/{original['id']}").json() == closed


def test_replacement_notes_at_combined_limit_preserve_the_final_customer_term() -> None:
    original = _create_quote()
    closed = client.post(
        f"/api/v1/customer-quotes/{original['id']}/status",
        json={"expected_revision": 1, "status": "expired"},
    ).json()
    predecessor = (
        f"Revision of {original['quote_number']} "
        f"(record {original['id']}, revision {closed['record_revision']}).\n"
    )
    notes = "N" * (10_000 - len(predecessor) - len("FINAL TERM")) + "FINAL TERM"
    response = client.post(
        f"/api/v1/customer-quotes/{original['id']}/revisions",
        json={**_payload(), "expected_revision": closed["record_revision"], "notes": notes},
    )
    assert response.status_code == 201, response.text
    assert response.json()["notes"] == predecessor + notes
    assert len(response.json()["notes"]) == 10_000
    assert response.json()["notes"].endswith("FINAL TERM")


@pytest.mark.parametrize("project_status", ["opportunity", "tendering", "awarded", "construction", "completed"])
def test_replacement_rejects_changed_project_name_without_side_effects(project_status: str) -> None:
    original = _create_quote()
    closed = client.post(
        f"/api/v1/customer-quotes/{original['id']}/status",
        json={"expected_revision": 1, "status": "declined"},
    ).json()
    with TestingSessionLocal() as db:
        from app.models.project import Project
        project = db.get(Project, UUID(original["project_id"]))
        project.status = project_status
        db.commit()
    project_before = client.get(f"/api/v1/projects/{original['project_id']}").json()
    quotes_before = client.get("/api/v1/customer-quotes").json()
    response = client.post(
        f"/api/v1/customer-quotes/{original['id']}/revisions",
        json={
            **_payload(), "expected_revision": closed["record_revision"],
            "project_name": "A different project name",
        },
    )
    assert response.status_code == 422, response.text
    assert "Keep the current project name" in response.json()["error"]["message"]
    assert client.get("/api/v1/customer-quotes").json() == quotes_before
    assert client.get(f"/api/v1/projects/{original['project_id']}").json() == project_before
