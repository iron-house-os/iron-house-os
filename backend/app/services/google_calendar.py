from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import base64
import hashlib
import json
from typing import Any
from uuid import UUID
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.schemas.google_calendar import GoogleCalendarEvent, GoogleCalendarEventCreate

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3"
REQUIRED_SCOPE = "https://www.googleapis.com/auth/calendar.events.owned"


class GoogleCalendarUnavailable(RuntimeError):
    pass


class GoogleCalendarAuthorizationExpired(GoogleCalendarUnavailable):
    pass


@dataclass(frozen=True)
class GoogleTokenResult:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scopes: list[str]


def calendar_is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.google_calendar_client_id
        and settings.google_calendar_client_secret
        and settings.google_calendar_redirect_uri
        and settings.google_calendar_token_encryption_key
    )


def authorization_url(state: str) -> str:
    settings = get_settings()
    if not calendar_is_configured():
        raise GoogleCalendarUnavailable("Google Calendar OAuth is not configured.")
    return f"{GOOGLE_AUTHORIZATION_URL}?{urlencode({
        'client_id': settings.google_calendar_client_id,
        'redirect_uri': settings.google_calendar_redirect_uri,
        'response_type': 'code',
        'scope': REQUIRED_SCOPE,
        'access_type': 'offline',
        'include_granted_scopes': 'true',
        'prompt': 'consent',
        'state': state,
    })}"


def state_digest(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def encrypt_token(token: str) -> str:
    return _cipher().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_token(encrypted_token: str) -> str:
    try:
        return _cipher().decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise GoogleCalendarUnavailable(
            "The stored Google Calendar connection cannot be decrypted. Reconnect the calendar."
        ) from exc


def exchange_authorization_code(
    code: str,
    existing_refresh_token: str | None = None,
) -> GoogleTokenResult:
    settings = get_settings()
    result = _form_request(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.google_calendar_client_id or "",
            "client_secret": settings.google_calendar_client_secret or "",
            "redirect_uri": settings.google_calendar_redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    return _token_result(result, refresh_token=existing_refresh_token)


def refresh_access_token(refresh_token: str) -> GoogleTokenResult:
    settings = get_settings()
    try:
        result = _form_request(
            GOOGLE_TOKEN_URL,
            {
                "refresh_token": refresh_token,
                "client_id": settings.google_calendar_client_id or "",
                "client_secret": settings.google_calendar_client_secret or "",
                "grant_type": "refresh_token",
            },
        )
    except GoogleCalendarUnavailable as exc:
        if "invalid_grant" in str(exc):
            raise GoogleCalendarAuthorizationExpired(
                "Google Calendar authorisation expired. Reconnect the calendar."
            ) from exc
        raise
    return _token_result(
        result,
        refresh_token=refresh_token,
        default_scopes=[REQUIRED_SCOPE],
    )


def list_primary_events(
    access_token: str,
    *,
    time_min: datetime,
    time_max: datetime,
    max_results: int = 50,
) -> list[GoogleCalendarEvent]:
    result = _calendar_request(
        access_token,
        "GET",
        "/calendars/primary/events",
        query={
            "timeMin": _rfc3339(time_min),
            "timeMax": _rfc3339(time_max),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": str(min(max(max_results, 1), 100)),
        },
    )
    events: list[GoogleCalendarEvent] = []
    for raw in result.get("items", []):
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        private = raw.get("extendedProperties", {}).get("private", {})
        project_id = None
        if isinstance(private, dict) and private.get("ihos_project_id"):
            try:
                project_id = UUID(str(private["ihos_project_id"]))
            except (TypeError, ValueError):
                project_id = None
        start = raw.get("start", {})
        end = raw.get("end", {})
        events.append(
            GoogleCalendarEvent(
                id=str(raw["id"]),
                title=str(raw.get("summary") or "Untitled event"),
                description=raw.get("description"),
                location=raw.get("location"),
                start=str(start.get("dateTime") or start.get("date") or ""),
                end=str(end.get("dateTime") or end.get("date") or ""),
                html_link=raw.get("htmlLink"),
                status=str(raw.get("status") or "confirmed"),
                project_id=project_id,
            )
        )
    return events


def create_primary_event(
    access_token: str,
    payload: GoogleCalendarEventCreate,
) -> GoogleCalendarEvent:
    body: dict[str, Any] = {
        "summary": payload.title.strip(),
        "start": {"dateTime": _rfc3339(payload.start)},
        "end": {"dateTime": _rfc3339(payload.end)},
    }
    if payload.description and payload.description.strip():
        body["description"] = payload.description.strip()
    if payload.location and payload.location.strip():
        body["location"] = payload.location.strip()
    if payload.project_id:
        body["extendedProperties"] = {
            "private": {"ihos_project_id": str(payload.project_id)}
        }
    raw = _calendar_request(
        access_token,
        "POST",
        "/calendars/primary/events",
        query={"sendUpdates": "none"},
        payload=body,
    )
    return GoogleCalendarEvent(
        id=str(raw["id"]),
        title=str(raw.get("summary") or payload.title),
        description=raw.get("description"),
        location=raw.get("location"),
        start=str(raw.get("start", {}).get("dateTime") or ""),
        end=str(raw.get("end", {}).get("dateTime") or ""),
        html_link=raw.get("htmlLink"),
        status=str(raw.get("status") or "confirmed"),
        project_id=payload.project_id,
    )


def revoke_token(token: str) -> None:
    request = Request(
        GOOGLE_REVOKE_URL,
        data=urlencode({"token": token}).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30):
            return
    except HTTPError as exc:
        if exc.code == 400:
            return
        raise GoogleCalendarUnavailable(
            f"Google Calendar token revocation failed ({exc.code})."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise GoogleCalendarUnavailable(
            "Google Calendar is temporarily unreachable."
        ) from exc


def _cipher() -> Fernet:
    settings = get_settings()
    source = settings.google_calendar_token_encryption_key
    if not source:
        raise GoogleCalendarUnavailable(
            "Google Calendar token encryption is not configured."
        )
    key = base64.urlsafe_b64encode(hashlib.sha256(source.encode("utf-8")).digest())
    return Fernet(key)


def _form_request(url: str, fields: dict[str, str]) -> dict:
    request = Request(
        url,
        data=urlencode(fields).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    return _read_json_response(request, timeout=45)


def _calendar_request(
    access_token: str,
    method: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    payload: dict | None = None,
) -> dict:
    url = f"{GOOGLE_CALENDAR_API_URL}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            **({"Content-Type": "application/json"} if body else {}),
        },
        method=method,
    )
    return _read_json_response(request, timeout=45)


def _read_json_response(request: Request, *, timeout: int) -> dict:
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        reason = _provider_reason(detail)
        raise GoogleCalendarUnavailable(
            f"Google Calendar rejected the request ({exc.code}): {reason}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise GoogleCalendarUnavailable(
            "Google Calendar is temporarily unreachable."
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GoogleCalendarUnavailable(
            "Google Calendar returned an invalid response."
        ) from exc


def _provider_reason(detail: str) -> str:
    try:
        parsed = json.loads(detail)
    except json.JSONDecodeError:
        return "provider_error"
    if isinstance(parsed, dict):
        if parsed.get("error") == "invalid_grant":
            return "invalid_grant"
        error = parsed.get("error")
        if isinstance(error, dict):
            errors = error.get("errors")
            if isinstance(errors, list) and errors and isinstance(errors[0], dict):
                return str(errors[0].get("reason") or "provider_error")[:120]
            return str(error.get("status") or "provider_error")[:120]
        if isinstance(error, str):
            return error[:120]
    return "provider_error"


def _token_result(
    result: dict,
    refresh_token: str | None = None,
    default_scopes: list[str] | None = None,
) -> GoogleTokenResult:
    access_token = result.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleCalendarUnavailable(
            "Google Calendar returned no access token."
        )
    returned_refresh = result.get("refresh_token")
    if isinstance(returned_refresh, str) and returned_refresh:
        refresh_token = returned_refresh
    expires_in = result.get("expires_in", 3600)
    try:
        expires_seconds = max(int(expires_in), 60)
    except (TypeError, ValueError):
        expires_seconds = 3600
    raw_scope = result.get("scope") or ""
    scopes = [scope for scope in str(raw_scope).split() if scope] or list(default_scopes or [])
    if REQUIRED_SCOPE not in scopes:
        raise GoogleCalendarUnavailable(
            "The required Google Calendar permission was not granted."
        )
    return GoogleTokenResult(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_seconds),
        scopes=scopes,
    )


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
