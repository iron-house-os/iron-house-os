from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.user import UserAccount
from app.services.auth import hash_password
from app.services.identity_governance import build_identity_governance_snapshot
from conftest import TestingSessionLocal

client = TestClient(app)
NOW = datetime(2026, 7, 24, 16, 0, tzinfo=timezone.utc)


def account(email: str, *, role: str = "viewer", active: bool = True) -> UserAccount:
    return UserAccount(
        email=email,
        display_name=email.split("@")[0].replace(".", " ").title(),
        role=role,
        password_hash=hash_password("Build-233-secure-password"),
        is_active=active,
    )


def test_snapshot_identifies_access_and_domain_risks_without_secrets() -> None:
    with TestingSessionLocal() as db:
        admin = account("jeremie@ironhousecontracting.com", role="admin")
        admin.created_at = NOW - timedelta(days=30)
        admin.last_login_at = NOW - timedelta(days=1)
        legacy = account("taryn@ironhousecivil.com")
        legacy.created_at = NOW - timedelta(days=100)
        legacy.last_login_at = NOW - timedelta(days=95)
        legacy.password_reset_required = True
        db.add_all([admin, legacy])
        db.commit()

        snapshot = build_identity_governance_snapshot(db, now=NOW)
        payload = snapshot.model_dump(mode="json")

    assert snapshot.summary.total_accounts == 2
    assert snapshot.summary.active_administrators == 1
    assert snapshot.summary.legacy_domain_accounts == 1
    assert snapshot.summary.accounts_requiring_review == 2
    assert [finding.code for finding in snapshot.findings][:2] == [
        "legacy_email_domain",
        "single_active_administrator",
    ]
    assert "password_hash" not in str(payload)
    assert "session_version" not in str(payload)


def test_governance_endpoint_is_administrator_only_and_has_stable_shape() -> None:
    response = client.get("/api/v1/users/governance")
    assert response.status_code == 200
    assert response.json()["canonical_email_domain"] == "ironhousecontracting.com"
    assert response.json()["summary"]["total_accounts"] == 0
    assert response.json()["findings"][0]["code"] == "no_active_administrator"
