from datetime import UTC, datetime, timedelta
import secrets
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.db.session import get_db
from app.models.calendar import GoogleCalendarConnection, GoogleCalendarOAuthState
from app.models.project import Project
from app.schemas.google_calendar import (
    GoogleCalendarAuthorization,
    GoogleCalendarDisconnect,
    GoogleCalendarEvent,
    GoogleCalendarEventCreate,
    GoogleCalendarStatus,
)
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.google_calendar import (
    REQUIRED_SCOPE,
    GoogleCalendarAuthorizationExpired,
    GoogleCalendarUnavailable,
    authorization_url,
    calendar_is_configured,
    create_primary_event,
    decrypt_token,
    encrypt_token,
    exchange_authorization_code,
    list_primary_events,
    refresh_access_token,
    revoke_token,
    state_digest,
)
from app.services.request_context import get_request_audit_context

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _require_management(user: CurrentUser) -> None:
    if user.role not in {"admin", "operations_manager"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management access is required.",
        )


def _require_enabled() -> None:
    if not get_settings().google_calendar_enabled:
        raise HTTPException(status_code=503, detail="Google Calendar is disabled.")


def _connection(db: Session, user: CurrentUser) -> GoogleCalendarConnection | None:
    return db.scalar(
        select(GoogleCalendarConnection).where(
            GoogleCalendarConnection.owner_account_id == user.id
        )
    )


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _access_token(
    db: Session,
    connection: GoogleCalendarConnection,
) -> str:
    now = datetime.now(UTC)
    expires_at = _aware(connection.token_expires_at)
    if (
        connection.encrypted_access_token
        and expires_at
        and expires_at > now + timedelta(seconds=60)
    ):
        return decrypt_token(connection.encrypted_access_token)
    if not connection.encrypted_refresh_token:
        connection.status = "disconnected"
        connection.last_error = "Reconnect Google Calendar."
        db.commit()
        raise HTTPException(status_code=409, detail="Reconnect Google Calendar.")
    refresh_token = decrypt_token(connection.encrypted_refresh_token)
    try:
        result = refresh_access_token(refresh_token)
    except GoogleCalendarAuthorizationExpired as exc:
        connection.encrypted_access_token = None
        connection.encrypted_refresh_token = None
        connection.token_expires_at = None
        connection.status = "disconnected"
        connection.last_error = str(exc)
        db.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GoogleCalendarUnavailable as exc:
        connection.last_error = str(exc)[:500]
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    connection.encrypted_access_token = encrypt_token(result.access_token)
    if result.refresh_token:
        connection.encrypted_refresh_token = encrypt_token(result.refresh_token)
    connection.token_expires_at = result.expires_at
    connection.scopes_json = result.scopes
    connection.status = "connected"
    connection.last_error = None
    db.commit()
    return result.access_token


def _return_url(outcome: str) -> str:
    settings = get_settings()
    separator = "&" if "?" in settings.google_calendar_frontend_return_url else "?"
    return (
        f"{settings.google_calendar_frontend_return_url}{separator}"
        f"{urlencode({'google_calendar': outcome})}"
    )


def _audit(
    request: Request,
    *,
    action: str,
    outcome: str,
    actor: str,
    metadata: dict,
) -> None:
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action=action,
            outcome=outcome,
            actor=actor,
            request_id=context.request_id,
            metadata=metadata,
        )
    )


@router.get("/status", response_model=GoogleCalendarStatus)
def google_calendar_status(user: CurrentUser, db: DBSession) -> GoogleCalendarStatus:
    _require_management(user)
    settings = get_settings()
    connection = _connection(db, user)
    connected = bool(
        connection
        and connection.status == "connected"
        and connection.encrypted_refresh_token
        and REQUIRED_SCOPE in connection.scopes_json
    )
    return GoogleCalendarStatus(
        enabled=settings.google_calendar_enabled,
        configured=calendar_is_configured(),
        connected=connected,
        status=connection.status if connection else "not_connected",
        required_scope=REQUIRED_SCOPE,
        last_synced_at=connection.last_synced_at if connection else None,
        last_error=connection.last_error if connection else None,
    )


@router.post("/oauth/start", response_model=GoogleCalendarAuthorization)
def start_google_calendar_oauth(
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> GoogleCalendarAuthorization:
    _require_management(user)
    _require_enabled()
    if not calendar_is_configured():
        raise HTTPException(status_code=503, detail="Google Calendar OAuth is not configured.")
    state = secrets.token_urlsafe(48)
    db.add(
        GoogleCalendarOAuthState(
            state_digest=state_digest(state),
            owner_account_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    db.commit()
    _audit(
        request,
        action="google_calendar_oauth_start",
        outcome="started",
        actor=user.email,
        metadata={"scope": REQUIRED_SCOPE},
    )
    return GoogleCalendarAuthorization(authorization_url=authorization_url(state))


@router.get("/oauth/callback", response_model=None)
def google_calendar_oauth_callback(
    request: Request,
    user: CurrentUser,
    db: DBSession,
    state: Annotated[str, Query(min_length=20, max_length=500)],
    code: Annotated[str | None, Query(max_length=4000)] = None,
    error: Annotated[str | None, Query(max_length=200)] = None,
):
    _require_management(user)
    _require_enabled()
    oauth_state = db.scalar(
        select(GoogleCalendarOAuthState).where(
            GoogleCalendarOAuthState.state_digest == state_digest(state),
            GoogleCalendarOAuthState.owner_account_id == user.id,
        )
    )
    if (
        oauth_state is None
        or oauth_state.used_at is not None
        or (_aware(oauth_state.expires_at) or datetime.min.replace(tzinfo=UTC))
        <= datetime.now(UTC)
    ):
        raise HTTPException(status_code=400, detail="The Google Calendar connection request expired.")
    oauth_state.used_at = datetime.now(UTC)
    db.commit()
    if error or not code:
        _audit(
            request,
            action="google_calendar_oauth_callback",
            outcome="denied",
            actor=user.email,
            metadata={"provider_error": (error or "missing_code")[:100]},
        )
        return RedirectResponse(_return_url("denied"), status_code=303)

    connection = _connection(db, user)
    existing_refresh = None
    if connection and connection.encrypted_refresh_token:
        existing_refresh = decrypt_token(connection.encrypted_refresh_token)
    try:
        result = exchange_authorization_code(code, existing_refresh)
    except GoogleCalendarUnavailable as exc:
        if connection:
            connection.last_error = str(exc)[:500]
            db.commit()
        _audit(
            request,
            action="google_calendar_oauth_callback",
            outcome="failed",
            actor=user.email,
            metadata={"reason": "provider_rejected"},
        )
        return RedirectResponse(_return_url("failed"), status_code=303)
    if not result.refresh_token:
        if connection:
            connection.last_error = "Google returned no offline access token. Reconnect and consent again."
            db.commit()
        return RedirectResponse(_return_url("failed"), status_code=303)
    if connection is None:
        connection = GoogleCalendarConnection(owner_account_id=user.id)
        db.add(connection)
    connection.encrypted_access_token = encrypt_token(result.access_token)
    connection.encrypted_refresh_token = encrypt_token(result.refresh_token)
    connection.token_expires_at = result.expires_at
    connection.scopes_json = result.scopes
    connection.status = "connected"
    connection.last_error = None
    db.commit()
    _audit(
        request,
        action="google_calendar_oauth_callback",
        outcome="connected",
        actor=user.email,
        metadata={"scope": REQUIRED_SCOPE},
    )
    return RedirectResponse(_return_url("connected"), status_code=303)


@router.get("/events", response_model=list[GoogleCalendarEvent])
def list_google_calendar_events(
    user: CurrentUser,
    db: DBSession,
    time_min: datetime | None = None,
    time_max: datetime | None = None,
) -> list[GoogleCalendarEvent]:
    _require_management(user)
    _require_enabled()
    connection = _connection(db, user)
    if connection is None or connection.status != "connected":
        raise HTTPException(status_code=409, detail="Connect Google Calendar first.")
    start = _aware(time_min) or datetime.now(UTC)
    end = _aware(time_max) or start + timedelta(days=90)
    if end <= start or end - start > timedelta(days=366):
        raise HTTPException(status_code=400, detail="Choose an event window of up to 366 days.")
    token = _access_token(db, connection)
    try:
        events = list_primary_events(token, time_min=start, time_max=end)
    except GoogleCalendarUnavailable as exc:
        connection.last_error = str(exc)[:500]
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    connection.last_synced_at = datetime.now(UTC)
    connection.last_error = None
    db.commit()
    return events


@router.post("/events", response_model=GoogleCalendarEvent, status_code=status.HTTP_201_CREATED)
def create_google_calendar_event(
    payload: GoogleCalendarEventCreate,
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> GoogleCalendarEvent:
    _require_management(user)
    _require_enabled()
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirm the event details before creating it.")
    if payload.project_id and db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    connection = _connection(db, user)
    if connection is None or connection.status != "connected":
        raise HTTPException(status_code=409, detail="Connect Google Calendar first.")
    token = _access_token(db, connection)
    try:
        event = create_primary_event(token, payload)
    except GoogleCalendarUnavailable as exc:
        connection.last_error = str(exc)[:500]
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    connection.last_synced_at = datetime.now(UTC)
    connection.last_error = None
    db.commit()
    _audit(
        request,
        action="google_calendar_event_create",
        outcome="completed",
        actor=user.email,
        metadata={
            "event_id": event.id,
            "project_id": str(payload.project_id) if payload.project_id else None,
            "start": payload.start.isoformat(),
            "end": payload.end.isoformat(),
            "send_updates": "none",
        },
    )
    return event


@router.post("/disconnect", response_model=GoogleCalendarStatus)
def disconnect_google_calendar(
    payload: GoogleCalendarDisconnect,
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> GoogleCalendarStatus:
    _require_management(user)
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirm Google Calendar disconnection.")
    connection = _connection(db, user)
    if connection and connection.encrypted_refresh_token:
        token = decrypt_token(connection.encrypted_refresh_token)
        try:
            revoke_token(token)
        except GoogleCalendarUnavailable as exc:
            connection.last_error = str(exc)[:500]
            db.commit()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    if connection:
        connection.encrypted_access_token = None
        connection.encrypted_refresh_token = None
        connection.token_expires_at = None
        connection.status = "disconnected"
        connection.last_error = None
        db.commit()
    _audit(
        request,
        action="google_calendar_disconnect",
        outcome="completed",
        actor=user.email,
        metadata={"tokens_cleared": True},
    )
    return GoogleCalendarStatus(
        enabled=get_settings().google_calendar_enabled,
        configured=calendar_is_configured(),
        connected=False,
        status="disconnected",
        required_scope=REQUIRED_SCOPE,
        last_synced_at=connection.last_synced_at if connection else None,
        last_error=None,
    )
