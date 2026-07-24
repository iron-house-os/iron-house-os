from datetime import date
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.core.config import get_settings
from app.main import app
from app.services import legal
from app.services.access_control import ModulePermission, can_access_module
from app.services.auth import AuthenticatedUser
from app.services.legal_specialists import active_authorities, authority_catalogue, triage_specialists


client = TestClient(app)


def _enable() -> None:
    get_settings().legal_control_enabled = True


def _matter(confidentiality: str = "standard") -> dict:
    response = client.post(
        "/api/v1/legal/matters",
        json={
            "title": "Synthetic subcontract review",
            "matter_type": "Contract review",
            "project_name": "Training Project",
            "counterparty": "Example Trade Ltd.",
            "description": "Review payment, change order, indemnity and insurance clauses before execution.",
            "confidentiality": confidentiality,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_legal_module_is_admin_only_and_defaults_off() -> None:
    assert can_access_module("admin", "legal", ModulePermission.READ)
    assert can_access_module("admin", "legal", ModulePermission.WRITE)
    for role in ("operations_manager", "estimator", "viewer"):
        assert not can_access_module(role, "legal", ModulePermission.READ)
    assert get_settings().legal_control_enabled is False


def test_authority_register_excludes_not_in_force_law_from_ai_sources() -> None:
    assert any(item["id"] == "bc-prompt-payment-act" and item["status"] == "not_in_force" for item in authority_catalogue())
    assert all(item["status"] == "active" for item in active_authorities())
    assert "bc-prompt-payment-act" not in {item["id"] for item in active_authorities()}
    assert "lien_payment" in triage_specialists("Unpaid holdback and builders lien concern")


def test_admin_can_create_matter_and_verify_human_deadline() -> None:
    _enable()
    matter = _matter()
    assert "contracts" in matter["assigned_specialists"]
    candidate = client.post(
        f"/api/v1/legal/matters/{matter['id']}/deadlines",
        json={"title": "Synthetic notice review", "due_date": date(2030, 1, 15).isoformat(), "source_basis": "Draft clause 8; counsel to confirm."},
    )
    assert candidate.status_code == 201
    assert candidate.json()["status"] == "candidate"
    verified = client.post(
        f"/api/v1/legal/deadlines/{candidate.json()['id']}/verify",
        json={"evidence_reference": "Reviewed contract clause 8 and counsel confirmation ref TEST-001."},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "verified"
    assert verified.json()["verified_by"] == "test-admin@ironhousecivil.com"


def test_analysis_is_source_controlled_and_stays_draft(monkeypatch) -> None:
    _enable()
    matter = _matter()

    def fake_analysis(**kwargs):
        assert all(source["status"] == "active" for source in kwargs["approved_sources"])
        return {
            "executive_summary": "Synthetic contract requires management and counsel review.",
            "draft_text": "Proposed clause [COUNSEL TO CONFIRM].",
            "issues": [{"issue": "Payment clause", "risk": "medium", "reasoning": "Review required.", "source_ids": ["bc-builders-lien-act"]}],
            "recommendations": [{"action": "Send clause to counsel", "owner": "Administrator", "urgency": "before signing", "source_ids": ["bc-builders-lien-act"]}],
            "questions_for_counsel": ["Confirm the final clause wording."],
            "source_ids": ["bc-builders-lien-act"],
            "disclaimer": "Draft only; counsel review required.",
        }

    monkeypatch.setattr(legal, "generate_legal_analysis", fake_analysis)
    response = client.post(f"/api/v1/legal/matters/{matter['id']}/analyse", json={"question": None})
    assert response.status_code == 201
    assert response.json()["status"] == "draft_requires_human_review"
    assert response.json()["source_ids"] == ["bc-builders-lien-act"]


def test_personal_or_privileged_matters_fail_closed_before_ai(monkeypatch) -> None:
    _enable()
    matter = _matter("personal_information")
    called = False

    def should_not_run(**kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(legal, "generate_legal_analysis", should_not_run)
    response = client.post(f"/api/v1/legal/matters/{matter['id']}/analyse", json={})
    assert response.status_code == 409
    assert "privacy" in response.json()["detail"].lower()
    assert called is False


def test_non_admin_is_denied_by_module_gate() -> None:
    _enable()

    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            email="test-operations@example.invalid",
            display_name="Test Operations",
            role="operations_manager",
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override
    assert client.get("/api/v1/legal/dashboard").status_code == 403
