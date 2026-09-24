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
from app.services import quickbooks as quickbooks_service
from app.services.quickbooks import (
    REQUIRED_SCOPE,
    QuickBooksCompanyInfo,
    QuickBooksUnavailable,
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
    assert callback.headers["cache-control"] == "no-store"
    assert callback.headers["referrer-policy"] == "no-referrer"

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
    assert replay.status_code == 303
    assert replay.headers["location"].endswith("?quickbooks=failed")
    assert replay.headers["cache-control"] == "no-store"
    assert replay.headers["referrer-policy"] == "no-referrer"


def test_oauth_state_consumption_is_atomic_compare_and_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    state = _start_state()

    with TestingSessionLocal() as db:
        assert quickbooks_routes._consume_oauth_state(
            db,
            state=state,
            owner_account_id=USER_ID,
        )
    with TestingSessionLocal() as db:
        assert not quickbooks_routes._consume_oauth_state(
            db,
            state=state,
            owner_account_id=USER_ID,
        )


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
    assert missing_realm.status_code == 303
    assert missing_realm.headers["location"].endswith("?quickbooks=failed")
    assert missing_realm.headers["cache-control"] == "no-store"
    assert missing_realm.headers["referrer-policy"] == "no-referrer"

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
    assert mismatch.status_code == 303
    assert mismatch.headers["location"].endswith("?quickbooks=failed")
    assert mismatch.headers["cache-control"] == "no-store"
    assert mismatch.headers["referrer-policy"] == "no-referrer"


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


def test_disconnect_remains_available_after_feature_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    _connected()
    revoked: list[str] = []
    monkeypatch.setattr(quickbooks_routes, "revoke_token", revoked.append)
    monkeypatch.setenv("QUICKBOOKS_ENABLED", "false")
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/finance/quickbooks/disconnect",
        json={"confirmed": True},
    )

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["connected"] is False
    assert revoked == ["refresh-token"]


def test_disconnect_clears_local_tokens_when_decryption_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    _connected()
    with TestingSessionLocal() as db:
        connection = db.query(QuickBooksConnection).one()
        connection.encrypted_refresh_token = "corrupt-ciphertext"
        db.commit()

    response = client.post(
        "/api/v1/finance/quickbooks/disconnect",
        json={"confirmed": True},
    )

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert "revocation could not be confirmed" in response.json()["last_error"]
    with TestingSessionLocal() as db:
        connection = db.query(QuickBooksConnection).one()
        assert connection.encrypted_access_token is None
        assert connection.encrypted_refresh_token is None


def test_token_result_accepts_omitted_scope_but_rejects_explicitly_insufficient_scope() -> None:
    result = quickbooks_service._token_result(
        {
            "access_token": "sandbox-access-token",
            "refresh_token": "sandbox-refresh-token",
            "expires_in": 3600,
        }
    )
    assert result.scopes == [REQUIRED_SCOPE]

    with pytest.raises(QuickBooksUnavailable, match="accounting permission"):
        quickbooks_service._token_result(
            {
                "access_token": "sandbox-access-token",
                "refresh_token": "sandbox-refresh-token",
                "scope": "openid profile",
            }
        )

    for invalid_scope in (None, [REQUIRED_SCOPE], {"scope": REQUIRED_SCOPE}):
        with pytest.raises(QuickBooksUnavailable, match="invalid permission response"):
            quickbooks_service._token_result(
                {
                    "access_token": "sandbox-access-token",
                    "refresh_token": "sandbox-refresh-token",
                    "scope": invalid_scope,
                }
            )


def test_revoke_token_uses_intuit_json_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    requests = []
    monkeypatch.setattr(
        quickbooks_service,
        "_read_json_response",
        lambda request: requests.append(request) or {},
    )

    quickbooks_service.revoke_token("sandbox-refresh-token")

    assert len(requests) == 1
    request = requests[0]
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads((request.data or b"").decode("utf-8")) == {
        "token": "sandbox-refresh-token"
    }


def test_tokens_are_encrypted_at_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    encrypted = encrypt_token("refresh-token-value")
    assert "refresh-token-value" not in encrypted
    assert decrypt_token(encrypted) == "refresh-token-value"
