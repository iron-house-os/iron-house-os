from datetime import date
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.bid import Bid
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


def test_quickbooks_export_contains_posted_cost_references() -> None:
    project = _project()
    client.post("/api/v1/finance/entries", json={"project_id": project["id"], "cost_code": "02-200", "entry_type": "actual", "category": "trucking", "amount": 1250.50, "entry_date": str(date.today()), "vendor_name": "Universal Trucking", "reference": "INV-226", "description": "Gravel haul", "status": "posted"})
    response = client.get(f"/api/v1/finance/projects/{project['id']}/quickbooks.csv")
    assert response.status_code == 200
    assert "INV-226" in response.text
    assert "Universal Trucking" in response.text
    assert "1250.50" in response.text


def test_financial_data_is_denied_to_non_management_accounts() -> None:
    project = _project()
    def estimator_user(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(id=UUID("00000000-0000-0000-0000-000000000026"), email="estimator@ironhousecivil.com", display_name="Estimator", role="estimator", session_version=1)
        request.state.authenticated_user = user
        return user
    app.dependency_overrides[require_authenticated_user] = estimator_user
    response = client.get(f"/api/v1/finance/projects/{project['id']}")
    assert response.status_code == 403
