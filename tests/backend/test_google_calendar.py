from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient
import pytest

from app.api.dependencies.auth import require_authenticated_user
from app.api.v1.routes import google_calendar as google_calendar_routes
from app.core.config import get_settings
from app.main import app
from app.models.calendar import GoogleCalendarConnection, GoogleCalendarOAuthState
from app.schemas.google_calendar import GoogleCalendarEvent
from app.services.auth import AuthenticatedUser
from app.services.google_calendar import (
    REQUIRED_SCOPE,
    GoogleTokenResult,
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
    monkeypatch.setenv("GOOGLE_CALENDAR_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "test-client.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "GOOGLE_CALENDAR_REDIRECT_URI",
        "https://os.ironhousecivil.com/api/v1/google-calendar/oauth/callback",
    )
    monkeypatch.setenv(
        "GOOGLE_CALENDAR_FRONTEND_RETURN_URL",
        "https://os.ironhousecivil.com/google-calendar",
    )
    monkeypatch.setenv("GOOGLE_CALENDAR_TOKEN_ENCRYPTION_KEY", "test-calendar-encryption-key")
    get_settings.cache_clear()


def _connected() -> None:
    with TestingSessionLocal() as db:
        db.add(
            GoogleCalendarConnection(
                owner_account_id=USER_ID,
                encrypted_access_token=encrypt_token("access-token"),
                encrypted_refresh_token=encrypt_token("refresh-token"),
                token_expires_at=datetime.now(UTC) + timedelta(hours=1),
                scopes_json=[REQUIRED_SCOPE],
                status="connected",
            )
        )
        db.commit()


def test_status_is_management_only_and_never_exposes_tokens() -> None:
    response = client.get("/api/v1/google-calendar/status")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["connected"] is False
    assert "token" not in body

    _authenticate_as("estimator")
    denied = client.get("/api/v1/google-calendar/status")
    assert denied.status_code == 403
    assert "google-calendar" in denied.json()["detail"]


def test_tokens_are_encrypted_at_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    encrypted = encrypt_token("refresh-token-value")
    assert "refresh-token-value" not in encrypted
    assert decrypt_token(encrypted) == "refresh-token-value"


def test_oauth_start_uses_narrow_scope_and_stores_only_state_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    response = client.post("/api/v1/google-calendar/oauth/start")
    assert response.status_code == 200
    authorization_url = response.json()["authorization_url"]
    query = parse_qs(urlparse(authorization_url).query)
    assert query["scope"] == [REQUIRED_SCOPE]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    state = query["state"][0]

    with TestingSessionLocal() as db:
        stored = db.query(GoogleCalendarOAuthState).one()
        assert stored.state_digest != state
        assert len(stored.state_digest) == 64
        assert stored.owner_account_id == USER_ID


def test_oauth_callback_is_single_use_and_encrypts_connection_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    start = client.post("/api/v1/google-calendar/oauth/start")
    state = parse_qs(urlparse(start.json()["authorization_url"]).query)["state"][0]
    monkeypatch.setattr(
        google_calendar_routes,
        "exchange_authorization_code",
        lambda code, existing_refresh_token=None: GoogleTokenResult(
            access_token="provider-access-token",
            refresh_token="provider-refresh-token",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=[REQUIRED_SCOPE],
        ),
    )
    callback = client.get(
        "/api/v1/google-calendar/oauth/callback",
        params={"state": state, "code": "provider-code"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert callback.headers["location"].endswith("?google_calendar=connected")

    with TestingSessionLocal() as db:
        connection = db.query(GoogleCalendarConnection).one()
        assert "provider-access-token" not in (connection.encrypted_access_token or "")
        assert "provider-refresh-token" not in (connection.encrypted_refresh_token or "")
        assert decrypt_token(connection.encrypted_refresh_token or "") == "provider-refresh-token"
        assert connection.scopes_json == [REQUIRED_SCOPE]

    replay = client.get(
        "/api/v1/google-calendar/oauth/callback",
        params={"state": state, "code": "provider-code"},
        follow_redirects=False,
    )
    assert replay.status_code == 400


def test_events_require_connection_and_explicit_write_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    disconnected = client.get("/api/v1/google-calendar/events")
    assert disconnected.status_code == 409
    _connected()
    event = GoogleCalendarEvent(
        id="google-event-1",
        title="Project coordination",
        start="2026-07-27T16:00:00Z",
        end="2026-07-27T17:00:00Z",
        status="confirmed",
        attendees=[],
        reminder_minutes=[30],
    )
    monkeypatch.setattr(
        google_calendar_routes,
        "list_primary_events",
        lambda token, time_min, time_max: [event],
    )
    listed = client.get("/api/v1/google-calendar/events")
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Project coordination"

    payload = {
        "title": "Project coordination",
        "start": "2026-07-27T09:00:00-07:00",
        "end": "2026-07-27T10:00:00-07:00",
        "project_id": None,
        "confirmed": False,
    }
    unconfirmed = client.post("/api/v1/google-calendar/events", json=payload)
    assert unconfirmed.status_code == 400
    naive_time = client.post(
        "/api/v1/google-calendar/events",
        json={
            **payload,
            "start": "2026-07-27T09:00:00",
            "end": "2026-07-27T10:00:00",
            "confirmed": True,
        },
    )
    assert naive_time.status_code == 422
    blank_title = client.post(
        "/api/v1/google-calendar/events",
        json={**payload, "title": "   ", "confirmed": True},
    )
    assert blank_title.status_code == 422

    monkeypatch.setattr(
        google_calendar_routes,
        "create_primary_event",
        lambda token, event_payload: event,
    )
    created = client.post(
        "/api/v1/google-calendar/events",
        json={**payload, "confirmed": True},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "google-event-1"


def test_attendees_require_explicit_invitation_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    _connected()
    payload = {
        "title": "Owner coordination",
        "start": "2026-07-27T09:00:00-07:00",
        "end": "2026-07-27T10:00:00-07:00",
        "attendees": ["MAC@ironhousecontracting.com"],
        "reminder_minutes": [30],
        "send_invitations": False,
        "confirmed": True,
    }
    blocked = client.post("/api/v1/google-calendar/events", json=payload)
    assert blocked.status_code == 422
    assert "Confirm attendee invitations" in str(blocked.json())


def test_disconnect_revokes_and_clears_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch)
    _connected()
    revoked: list[str] = []
    monkeypatch.setattr(google_calendar_routes, "revoke_token", revoked.append)

    response = client.post(
        "/api/v1/google-calendar/disconnect",
        json={"confirmed": True},
    )
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert revoked == ["refresh-token"]
    with TestingSessionLocal() as db:
        connection = db.query(GoogleCalendarConnection).one()
        assert connection.status == "disconnected"
        assert connection.encrypted_access_token is None
        assert connection.encrypted_refresh_token is None
