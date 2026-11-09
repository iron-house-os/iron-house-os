from copy import deepcopy
from datetime import date
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.bid import Bid
from app.models.project import Project
from app.services.auth import AuthenticatedUser
from conftest import TestingSessionLocal

client = TestClient(app)


def _project() -> dict:
    response = client.post("/api/v1/projects", json={"name": "Financial Control Test", "project_number": "FIN-226"})
    assert response.status_code == 201
    return response.json()


def _estimate(project_id: str) -> UUID:
    with TestingSessionLocal() as db:
        bid = Bid(project_id=UUID(project_id), status="approved", total_amount=150000, summary="Approved estimate", bid_json={"summary": {"final_price": 150000, "line_items": [{"code": "03-100", "description": "Storm main", "item_type": "material", "direct_cost": 100000}], "indirect_cost": 10000, "risk_cost": 5000, "contingency": 5000, "bonding": 1000, "insurance": 1000, "overhead": 10000}})
        db.add(bid)
        db.commit()
        db.refresh(bid)
        return bid.id


def _bennett_style_estimate(project_id: str) -> UUID:
    with TestingSessionLocal() as db:
        project = db.get(Project, UUID(project_id))
        assert project is not None
        project.metadata_json = {
            "award_pricing_baseline": {
                "source_quote_id": "quote-1",
                "source_quote_number": "Q-2026-002",
                "pricing_subtotal": "36266.67",
                "cost_budget_status": "needs_cost_allocation",
                "lines": [{"description": "Concrete pull and pour", "cost_code": None}],
            },
            "procurement_plan": {
                "status": "draft",
                "automatic_commitment": False,
                "requirements": [],
            },
        }
        bid = Bid(
            project_id=UUID(project_id),
            status="approved",
            total_amount=36266.67,
            summary="Bennett concrete estimate",
            bid_json={
                "source": "bennett_strata_issue_314",
                "source_revision": "2026-08-27-final",
                "estimate_key": "concrete",
                "estimate": {
                    "risks": [
                        {
                            "description": "Subgrade / buried deficiencies provisional allowance",
                            "amount": 4750,
                            "probability": 1,
                        }
                    ]
                },
                "summary": {
                    "final_price": 36266.67,
                    "line_items": [
                        {"code": "CON-001", "description": "4 in concrete pull and pour", "item_type": "self_perform", "quantity": 108.6, "unit": "m2", "direct_cost": 19860.93},
                        {"code": "EQP-001", "description": "14 in cutoff saw", "item_type": "equipment", "quantity": 1, "unit": "day", "direct_cost": 200},
                        {"code": "EQP-002", "description": "Skid steer with hydraulic hammer", "item_type": "equipment", "quantity": 1, "unit": "day", "direct_cost": 1100},
                        {"code": "TRK-001", "description": "Concrete disposal tandem", "item_type": "subcontract", "quantity": 1, "unit": "LS", "direct_cost": 750},
                    ],
                    "indirect_cost": 0,
                    "risk_cost": 4750,
                    "contingency": 0,
                    "bonding": 0,
                    "insurance": 0,
                    "overhead": 0,
                },
            },
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)
        return bid.id


def _bennett_budget_payload(workspace_id: UUID) -> dict:
    return {
        "workspace_id": str(workspace_id),
        "cost_code_mappings": {
            "CON-001": "4100",
            "EQP-001": "5100",
            "EQP-002": "5110",
            "TRK-001": "6100",
        },
        "cost_code_names": {
            "4100": "Concrete restoration",
            "5100": "Small equipment rental",
            "5110": "Skid steer / hydraulic attachment",
            "6100": "Trucking, disposal and material hauling",
        },
        "risk_cost_code": "4100",
        "risk_cost_code_name": "Concrete restoration",
    }


def _bennett_procurement_requirements() -> list[dict]:
    return [
        {
            "source_code": "CON-001",
            "category": "material",
            "description": "Ready-mix concrete planning requirement",
            "order_quantity": None,
            "order_unit": "m3",
            "order_quantity_status": "needs_confirmation",
            "specification": "4 in concrete scope; mix, order quantity, delivery and placement details require confirmation.",
        },
        {
            "source_code": "EQP-001",
            "category": "rental",
            "description": "14 in cutoff saw including blade wear and consumables",
            "order_quantity": "1",
            "order_unit": "day",
            "order_quantity_status": "planning_basis",
        },
        {
            "source_code": "EQP-002",
            "category": "rental",
            "description": "Skid steer with hydraulic hammer",
            "order_quantity": "1",
            "order_unit": "day",
            "order_quantity_status": "planning_basis",
        },
        {
            "source_code": "TRK-001",
            "category": "trucking",
            "description": "Tandem allowance for concrete disposal",
            "order_quantity": "1",
            "order_unit": "LS",
            "order_quantity_status": "planning_basis",
        },
    ]


def test_estimate_budget_actual_commitment_and_forecast_summary() -> None:
    project = _project()
    workspace_id = _estimate(project["id"])
    imported = client.post(f"/api/v1/finance/projects/{project['id']}/import-estimate", json={"workspace_id": str(workspace_id)})
    assert imported.status_code == 200
    assert imported.json()["budget"] == 132000
    assert imported.json()["contract_value"] == 150000
    commitment = client.post("/api/v1/finance/entries", json={"project_id": project["id"], "cost_code": "03-100", "entry_type": "commitment", "category": "material", "amount": 40000, "entry_date": str(date.today()), "vendor_name": "EMCO", "reference": "PO-0001", "status": "open"})
    assert commitment.status_code == 201
    actual = client.post("/api/v1/finance/entries", json={"project_id": project["id"], "cost_code": "03-100", "entry_type": "actual", "category": "material", "amount": 25000, "entry_date": str(date.today()), "vendor_name": "EMCO", "reference": "INV-100", "status": "posted"})
    assert actual.status_code == 201
    summary = client.get(f"/api/v1/finance/projects/{project['id']}").json()
    assert summary["committed"] == 40000
    assert summary["actual"] == 25000
    assert summary["forecast_cost"] == 65000
    assert summary["forecast_profit"] == 85000


def test_estimate_budget_mapping_is_idempotent_and_initializes_job_cost_codes() -> None:
    project = _project()
    awarded = client.patch(f"/api/v1/projects/{project['id']}", json={"status": "awarded"})
    assert awarded.status_code == 200
    workspace_id = _bennett_style_estimate(project["id"])
    payload = _bennett_budget_payload(workspace_id)

    first = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )
    second = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["budget"] == 26660.93
    assert second.json()["budget"] == 26660.93
    first_entries = [item for item in first.json()["entries"] if item["entry_type"] == "budget"]
    second_entries = [item for item in second.json()["entries"] if item["entry_type"] == "budget"]
    assert len(first_entries) == len(second_entries) == 5
    assert {item["id"] for item in first_entries} == {item["id"] for item in second_entries}
    assert all(item["source_key"] for item in first_entries)
    code_totals = {item["cost_code"]: item["budget"] for item in second.json()["cost_codes"]}
    assert code_totals == {"4100": 24610.93, "5100": 200, "5110": 1100, "6100": 750}
    refreshed = client.get(f"/api/v1/projects/{project['id']}").json()
    baseline = refreshed["metadata"]["award_pricing_baseline"]
    assert baseline["pricing_subtotal"] == "36266.67"
    assert baseline["cost_budget_status"] == "allocated"
    assert baseline["cost_budget_total"] == "26660.93"
    assert len(baseline["cost_budget_lines"]) == 5
    assert refreshed["metadata"]["project_cost_codes"] == [
        {"code": "4100", "name": "Concrete restoration"},
        {"code": "5100", "name": "Small equipment rental"},
        {"code": "5110", "name": "Skid steer / hydraulic attachment"},
        {"code": "6100", "name": "Trucking, disposal and material hauling"},
    ]
    assert refreshed["metadata"]["procurement_plan"]["automatic_commitment"] is False
    launch = client.get(f"/api/v1/projects/{project['id']}/launch-dashboard").json()
    assert launch["baseline_budget_total"] == 26660.93
    assert launch["budget_entry_count"] == 5
    assert launch["award_cost_budget_status"] == "allocated"
    assert launch["uncoded_award_line_count"] == 0
    timesheets = client.get("/api/v1/daily-timesheets/bootstrap").json()
    assert timesheets["project_cost_codes"][project["id"]] == [
        {"code": "4100", "name": "Concrete restoration"},
        {"code": "5100", "name": "Small equipment rental"},
        {"code": "5110", "name": "Skid steer / hydraulic attachment"},
        {"code": "6100", "name": "Trucking, disposal and material hauling"},
    ]


def test_estimate_budget_reactivates_a_previously_voided_source_key() -> None:
    project = _project()
    workspace_id = _bennett_style_estimate(project["id"])
    payload = _bennett_budget_payload(workspace_id)
    first = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )
    assert first.status_code == 200
    trucking = next(item for item in first.json()["entries"] if item["cost_code"] == "6100")

    with TestingSessionLocal() as db:
        bid = db.get(Bid, workspace_id)
        assert bid is not None
        estimate = deepcopy(bid.bid_json)
        estimate["summary"]["line_items"][3]["direct_cost"] = 0
        bid.bid_json = estimate
        db.commit()
    reduced = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )
    assert reduced.status_code == 200
    assert reduced.json()["budget"] == 25910.93
    assert all(item["cost_code"] != "6100" for item in reduced.json()["entries"])

    with TestingSessionLocal() as db:
        bid = db.get(Bid, workspace_id)
        assert bid is not None
        estimate = deepcopy(bid.bid_json)
        estimate["summary"]["line_items"][3]["direct_cost"] = 750
        bid.bid_json = estimate
        db.commit()
    restored = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )
    assert restored.status_code == 200
    restored_trucking = next(
        item for item in restored.json()["entries"] if item["cost_code"] == "6100"
    )
    assert restored.json()["budget"] == 26660.93
    assert restored_trucking["id"] == trucking["id"]


def test_estimate_budget_seeds_source_linked_procurement_planning_without_commitments() -> None:
    project = _project()
    awarded = client.patch(f"/api/v1/projects/{project['id']}", json={"status": "awarded"})
    assert awarded.status_code == 200
    workspace_id = _bennett_style_estimate(project["id"])
    payload = _bennett_budget_payload(workspace_id)
    payload["procurement_requirements"] = _bennett_procurement_requirements()

    first = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )
    second = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["budget"] == second.json()["budget"] == 26660.93
    assert {item["id"] for item in first.json()["entries"]} == {
        item["id"] for item in second.json()["entries"]
    }
    refreshed = client.get(f"/api/v1/projects/{project['id']}").json()
    plan = refreshed["metadata"]["procurement_plan"]
    assert plan["status"] == "draft"
    assert plan["job_number"] == awarded.json()["project_number"]
    assert plan["source_estimate_workspace_id"] == str(workspace_id)
    assert plan["automatic_commitment"] is False
    requirements = plan["requirements"]
    assert len(requirements) == 4
    assert len({item["requirement_id"] for item in requirements}) == 4
    assert [item["source_code"] for item in requirements] == [
        "CON-001",
        "EQP-001",
        "EQP-002",
        "TRK-001",
    ]
    assert [item["cost_code"] for item in requirements] == ["4100", "5100", "5110", "6100"]
    assert [item["budget_basis"] for item in requirements] == [
        "19860.93",
        "200.00",
        "1100.00",
        "750.00",
    ]
    assert all(
        item["budget_basis_type"] == "source_estimate_line_cost_not_authorized_spend"
        for item in requirements
    )
    concrete = requirements[0]
    assert concrete["scope_quantity"] == "108.6"
    assert concrete["scope_unit"] == "m2"
    assert concrete["order_quantity"] is None
    assert concrete["order_unit"] == "m3"
    assert concrete["order_quantity_status"] == "needs_confirmation"
    assert concrete["status"] == "needs_quantity_confirmation"
    assert all(
        item[field] is None
        for item in requirements
        for field in (
            "vendor_id",
            "vendor_quote_reference",
            "required_on_site_date",
            "approval",
            "po_number",
        )
    )
    assert all(item["commitment_created"] is False for item in requirements)
    assert not any(item["source_code"] == "RISK" for item in requirements)
    launch = client.get(f"/api/v1/projects/{project['id']}/launch-dashboard").json()
    assert launch["procurement_requirement_count"] == 4
    assert launch["procurement_plan_status"] == "draft"
    assert launch["po_request_count"] == 0


def test_estimate_procurement_plan_does_not_replace_a_vendor_decision() -> None:
    project = _project()
    awarded = client.patch(f"/api/v1/projects/{project['id']}", json={"status": "awarded"})
    assert awarded.status_code == 200
    workspace_id = _bennett_style_estimate(project["id"])
    payload = _bennett_budget_payload(workspace_id)
    payload["procurement_requirements"] = _bennett_procurement_requirements()
    created = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )
    assert created.status_code == 200

    with TestingSessionLocal() as db:
        row = db.get(Project, UUID(project["id"]))
        assert row is not None
        metadata = deepcopy(row.metadata_json)
        metadata["procurement_plan"]["requirements"][1]["approval"] = {
            "status": "approved",
            "by": "manager@ironhousecontracting.com",
        }
        row.metadata_json = metadata
        db.commit()
    blocked = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json=payload,
    )

    assert blocked.status_code == 409
    assert "decision or commitment" in blocked.json()["detail"]
    unchanged = client.get(f"/api/v1/projects/{project['id']}").json()
    assert unchanged["metadata"]["procurement_plan"]["requirements"][1]["approval"] == {
        "status": "approved",
        "by": "manager@ironhousecontracting.com",
    }


def test_estimate_budget_import_does_not_replace_a_manual_budget() -> None:
    project = _project()
    workspace_id = _estimate(project["id"])
    manual = client.post(
        "/api/v1/finance/entries",
        json={
            "project_id": project["id"],
            "cost_code": "MANUAL",
            "entry_type": "budget",
            "category": "other",
            "amount": 100,
            "entry_date": str(date.today()),
            "description": "Management-entered budget",
        },
    )
    assert manual.status_code == 201

    blocked = client.post(
        f"/api/v1/finance/projects/{project['id']}/import-estimate",
        json={"workspace_id": str(workspace_id)},
    )

    assert blocked.status_code == 409
    assert "manual or different-workspace budget" in blocked.json()["detail"]
    summary = client.get(f"/api/v1/finance/projects/{project['id']}").json()
    assert summary["budget"] == 100


def test_quickbooks_export_contains_posted_cost_references() -> None:
    project = _project()
    client.post("/api/v1/finance/entries", json={"project_id": project["id"], "cost_code": "02-200", "entry_type": "actual", "category": "trucking", "amount": 1250.50, "entry_date": str(date.today()), "vendor_name": "Universal Trucking", "reference": "INV-226", "description": "Gravel haul", "status": "posted"})
    response = client.get(f"/api/v1/finance/projects/{project['id']}/quickbooks.csv")
    assert response.status_code == 200
    assert "INV-226" in response.text
    assert "Universal Trucking" in response.text
    assert "1250.50" in response.text


def test_startup_expenses_build_owner_loan_until_reimbursed() -> None:
    created = client.post("/api/v1/finance/startup-expenses", json={"expense_date": str(date.today()), "vendor_name": "Apple", "description": "Business cloud storage", "amount": 12.99, "category": "software", "reference": "MN0HT72V12", "funding_source": "owner_loan", "owner_name": "Jeremie Peters", "tax_treatment": "needs_review", "status": "review", "receipt_metadata": {"source": "gmail"}})
    assert created.status_code == 201
    expense_id = created.json()["id"]
    summary = client.get("/api/v1/finance/startup-expenses").json()
    assert summary["owner_loan_payable"] >= 12.99
    approved = client.patch(f"/api/v1/finance/startup-expenses/{expense_id}", json={"status": "approved"})
    assert approved.status_code == 200
    summary = client.get("/api/v1/finance/startup-expenses").json()
    assert summary["approved_unreimbursed"] >= 12.99
    reimbursed = client.patch(f"/api/v1/finance/startup-expenses/{expense_id}", json={"status": "reimbursed"})
    assert reimbursed.status_code == 200
    summary = client.get("/api/v1/finance/startup-expenses").json()
    assert summary["reimbursed_to_owner"] >= 12.99


def test_financial_data_is_denied_to_non_management_accounts() -> None:
    project = _project()
    def estimator_user(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(id=UUID("00000000-0000-0000-0000-000000000026"), email="estimator@ironhousecontracting.com", display_name="Estimator", role="estimator", session_version=1)
        request.state.authenticated_user = user
        return user
    app.dependency_overrides[require_authenticated_user] = estimator_user
    response = client.get(f"/api/v1/finance/projects/{project['id']}")
    assert response.status_code == 403
