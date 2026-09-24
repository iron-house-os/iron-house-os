from datetime import UTC, datetime, timedelta
import json
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient
import pytest

from app.api.dependencies.auth import require_authenticated_user
from app.api.v1.routes import quickbooks as quickbooks_routes
from app.core.config import get_settings
from app.main import app
from app.models.quickbooks import QuickBooksConnection, QuickBooksOAuthState
from app.services.auth import AuthenticatedUser
from app.services.quickbooks import (
    REQUIRED_SCOPE,
    QuickBooksCompanyInfo,
    QuickBooksTokenResult,
    decrypt_token,
    encrypt_token,
)
from conftest import TestingSessionLocal

client = TestClient(app)
USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=USER_ID,
            email=f"{role}@ironhousecontracting.com",
            display_name=f"Test {role}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _configure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUICKBOOKS_ENABLED", "true")
    monkeypatch.setenv("QUICKBOOKS_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("QUICKBOOKS_CLIENT_ID", "sandbox-client-id")
    monkeypatch.setenv("QUICKBOOKS_CLIENT_SECRET", "sandbox-client-secret-value")
    monkeypatch.setenv(
        "QUICKBOOKS_REDIRECT_URI",
        "https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback",
    )
    monkeypatch.setenv(
        "QUICKBOOKS_FRONTEND_RETURN_URL",
        "https://os.ironhousecivil.com/finance",
    )
    monkeypatch.setenv(
        "QUICKBOOKS_TOKEN_ENCRYPTION_KEY",
        "test-quickbooks-encryption-key-with-enough-length",
    )
    get_settings.cache_clear()


def _start_state() -> str:
    response = client.post("/api/v1/finance/quickbooks/oauth/start")
    assert response.status_code == 200
    return parse_qs(urlparse(response.json()["authorization_url"]).query)["state"][0]


def _connected(*, realm_id: str = "9341457990023688") -> None:
    with TestingSessionLocal() as db:
        db.add(
            QuickBooksConnection(
                environment="sandbox",
                connected_by_account_id=USER_ID,
                realm_id=realm_id,
                company_name="Sandbox Company US 3969",
                legal_name="Sandbox Company US 3969",
                encrypted_access_token=encrypt_token("access-token"),
                encrypted_refresh_token=encrypt_token("refresh-token"),
                token_expires_at=datetime.now(UTC) + timedelta(hours=1),
                refresh_token_expires_at=datetime.now(UTC) + timedelta(days=100),
                scopes_json=[REQUIRED_SCOPE],
                status="connected",
                last_verified_at=datetime.now(UTC),
            )
        )
        db.commit()


def test_status_is_admin_only_and_never_exposes_tokens() -> None:
    response = client.get("/api/v1/finance/quickbooks/status")
    assert response.status_code == 200
    body = response.json()
    assert body["environment"] == "sandbox"
    assert body["connected"] is False
    assert "token" not in json.dumps(body).lower()

    _authenticate_as("operations_manager")
    denied = client.get("/api/v1/finance/quickbooks/status")
    assert denied.status_code == 403
    assert "Administrator" in denied.json()["detail"]


def test_oauth_start_uses_accounting_scope_and_stores_only_state_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    response = client.post("/api/v1/finance/quickbooks/oauth/start")
    assert response.status_code == 200
    query = parse_qs(urlparse(response.json()["authorization_url"]).query)
    assert query["scope"] == [REQUIRED_SCOPE]
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == [
        "https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback"
    ]
    state = query["state"][0]

    with TestingSessionLocal() as db:
        stored = db.query(QuickBooksOAuthState).one()
        assert stored.state_digest != state
        assert len(stored.state_digest) == 64
        assert stored.environment == "sandbox"


def test_oauth_callback_is_single_use_binds_company_and_encrypts_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    state = _start_state()
    monkeypatch.setattr(
        quickbooks_routes,
        "exchange_authorization_code",
        lambda code, existing_refresh_token=None: QuickBooksTokenResult(
            access_token="provider-access-token",
            refresh_token="provider-refresh-token",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token_expires_at=datetime.now(UTC) + timedelta(days=100),
            scopes=[REQUIRED_SCOPE],
        ),
    )
    monkeypatch.setattr(
        quickbooks_routes,
        "get_company_info",
        lambda token, realm_id: QuickBooksCompanyInfo(
            company_name="Sandbox Company US 3969",
            legal_name="Sandbox Company US 3969",
        ),
    )
    callback = client.get(
        "/api/v1/finance/quickbooks/oauth/callback",
        params={"state": state, "code": "provider-code", "realmId": "9341457990023688"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert callback.headers["location"].endswith("?quickbooks=connected")

    with TestingSessionLocal() as db:
        connection = db.query(QuickBooksConnection).one()
        assert connection.environment == "sandbox"
        assert connection.realm_id == "9341457990023688"
        assert connection.company_name == "Sandbox Company US 3969"
        assert "provider-access-token" not in (connection.encrypted_access_token or "")
        assert "provider-refresh-token" not in (connection.encrypted_refresh_token or "")
        assert decrypt_token(connection.encrypted_refresh_token or "") == "provider-refresh-token"

    replay = client.get(
        "/api/v1/finance/quickbooks/oauth/callback",
        params={"state": state, "code": "provider-code", "realmId": "9341457990023688"},
        follow_redirects=False,
    )
    assert replay.status_code == 400


def test_callback_rejects_incomplete_response_and_different_bound_realm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    missing_realm_state = _start_state()
    missing_realm = client.get(
        "/api/v1/finance/quickbooks/oauth/callback",
        params={"state": missing_realm_state, "code": "provider-code"},
        follow_redirects=False,
    )
    assert missing_realm.status_code == 400

    _connected(realm_id="1111111111111111")
    different_realm_state = _start_state()
    mismatch = client.get(
        "/api/v1/finance/quickbooks/oauth/callback",
        params={
            "state": different_realm_state,
            "code": "provider-code",
            "realmId": "2222222222222222",
        },
        follow_redirects=False,
    )
    assert mismatch.status_code == 409
    assert "different company" in mismatch.json()["detail"]


def test_disconnect_requires_confirmation_revokes_and_clears_local_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    _connected()
    revoked: list[str] = []
    monkeypatch.setattr(quickbooks_routes, "revoke_token", revoked.append)

    denied = client.post(
        "/api/v1/finance/quickbooks/disconnect",
        json={"confirmed": False},
    )
    assert denied.status_code == 400

    response = client.post(
        "/api/v1/finance/quickbooks/disconnect",
        json={"confirmed": True},
    )
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["status"] == "disconnected"
    assert revoked == ["refresh-token"]

    with TestingSessionLocal() as db:
        connection = db.query(QuickBooksConnection).one()
        assert connection.encrypted_access_token is None
        assert connection.encrypted_refresh_token is None


def test_tokens_are_encrypted_at_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    encrypted = encrypt_token("refresh-token-value")
    assert "refresh-token-value" not in encrypted
    assert decrypt_token(encrypted) == "refresh-token-value"
