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
from app.models.quickbooks import QuickBooksConnection, QuickBooksOAuthState
from app.schemas.quickbooks import (
    QuickBooksAuthorization,
    QuickBooksDisconnect,
    QuickBooksStatus,
)
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.quickbooks import (
    REQUIRED_SCOPE,
    QuickBooksUnavailable,
    authorization_url,
    decrypt_token,
    encrypt_token,
    exchange_authorization_code,
    get_company_info,
    quickbooks_is_configured,
    revoke_token,
    state_digest,
)
from app.services.request_context import get_request_audit_context

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _require_admin(user: CurrentUser) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required for the QuickBooks connection.",
        )


def _require_enabled() -> None:
    settings = get_settings()
    if not settings.quickbooks_enabled:
        raise HTTPException(status_code=503, detail="QuickBooks sandbox connection is disabled.")
    if settings.quickbooks_environment.strip().lower() != "sandbox":
        raise HTTPException(
            status_code=503,
            detail="Only the approved QuickBooks sandbox connection is available.",
        )


def _connection(db: Session) -> QuickBooksConnection | None:
    return db.scalar(
        select(QuickBooksConnection).where(QuickBooksConnection.environment == "sandbox")
    )


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _status(db: Session) -> QuickBooksStatus:
    settings = get_settings()
    connection = _connection(db)
    connected = bool(
        connection
        and connection.status == "connected"
        and connection.encrypted_refresh_token
        and REQUIRED_SCOPE in connection.scopes_json
    )
    return QuickBooksStatus(
        enabled=settings.quickbooks_enabled,
        configured=quickbooks_is_configured(),
        connected=connected,
        status=connection.status if connection else "not_connected",
        environment="sandbox",
        required_scope=REQUIRED_SCOPE,
        realm_id=connection.realm_id if connection else None,
        company_name=connection.company_name if connection else None,
        legal_name=connection.legal_name if connection else None,
        last_verified_at=connection.last_verified_at if connection else None,
        last_error=connection.last_error if connection else None,
    )


def _return_url(outcome: str) -> str:
    target = get_settings().quickbooks_frontend_return_url
    separator = "&" if "?" in target else "?"
    return f"{target}{separator}{urlencode({'quickbooks': outcome})}"


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


@router.get("/status", response_model=QuickBooksStatus)
def quickbooks_status(user: CurrentUser, db: DBSession) -> QuickBooksStatus:
    _require_admin(user)
    return _status(db)


@router.post("/oauth/start", response_model=QuickBooksAuthorization)
def start_quickbooks_oauth(
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> QuickBooksAuthorization:
    _require_admin(user)
    _require_enabled()
    if not quickbooks_is_configured():
        raise HTTPException(status_code=503, detail="QuickBooks sandbox OAuth is not configured.")
    state = secrets.token_urlsafe(48)
    db.add(
        QuickBooksOAuthState(
            state_digest=state_digest(state),
            owner_account_id=user.id,
            environment="sandbox",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    db.commit()
    _audit(
        request,
        action="quickbooks_oauth_start",
        outcome="started",
        actor=user.email,
        metadata={"environment": "sandbox", "scope": REQUIRED_SCOPE},
    )
    return QuickBooksAuthorization(authorization_url=authorization_url(state))


@router.get("/oauth/callback", response_model=None)
def quickbooks_oauth_callback(
    request: Request,
    user: CurrentUser,
    db: DBSession,
    state: Annotated[str, Query(min_length=20, max_length=500)],
    code: Annotated[str | None, Query(max_length=4000)] = None,
    realm_id: Annotated[str | None, Query(alias="realmId", min_length=1, max_length=64)] = None,
    error: Annotated[str | None, Query(max_length=200)] = None,
):
    _require_admin(user)
    _require_enabled()
    oauth_state = db.scalar(
        select(QuickBooksOAuthState).where(
            QuickBooksOAuthState.state_digest == state_digest(state),
            QuickBooksOAuthState.owner_account_id == user.id,
            QuickBooksOAuthState.environment == "sandbox",
        )
    )
    if (
        oauth_state is None
        or oauth_state.used_at is not None
        or (_aware(oauth_state.expires_at) or datetime.min.replace(tzinfo=UTC))
        <= datetime.now(UTC)
    ):
        raise HTTPException(status_code=400, detail="The QuickBooks connection request expired.")
    oauth_state.used_at = datetime.now(UTC)
    db.commit()

    if error:
        _audit(
            request,
            action="quickbooks_oauth_callback",
            outcome="denied",
            actor=user.email,
            metadata={"environment": "sandbox", "provider_error": error[:100]},
        )
        return RedirectResponse(_return_url("denied"), status_code=303)
    if not code or not realm_id:
        raise HTTPException(status_code=400, detail="QuickBooks returned an incomplete authorization response.")

    connection = _connection(db)
    if connection and connection.status == "connected" and connection.realm_id != realm_id:
        raise HTTPException(
            status_code=409,
            detail="Disconnect the current QuickBooks sandbox company before connecting a different company.",
        )
    existing_refresh = None
    if connection and connection.encrypted_refresh_token:
        existing_refresh = decrypt_token(connection.encrypted_refresh_token)
    try:
        result = exchange_authorization_code(code, existing_refresh)
        if not result.refresh_token:
            raise QuickBooksUnavailable("QuickBooks returned no refresh token.")
        company = get_company_info(result.access_token, realm_id)
    except QuickBooksUnavailable as exc:
        if connection:
            connection.last_error = str(exc)[:500]
            db.commit()
        _audit(
            request,
            action="quickbooks_oauth_callback",
            outcome="failed",
            actor=user.email,
            metadata={"environment": "sandbox", "reason": "provider_rejected"},
        )
        return RedirectResponse(_return_url("failed"), status_code=303)

    if connection is None:
        connection = QuickBooksConnection(
            environment="sandbox",
            connected_by_account_id=user.id,
            realm_id=realm_id,
            company_name=company.company_name,
        )
        db.add(connection)
    connection.connected_by_account_id = user.id
    connection.realm_id = realm_id
    connection.company_name = company.company_name
    connection.legal_name = company.legal_name
    connection.encrypted_access_token = encrypt_token(result.access_token)
    connection.encrypted_refresh_token = encrypt_token(result.refresh_token)
    connection.token_expires_at = result.expires_at
    connection.refresh_token_expires_at = result.refresh_token_expires_at
    connection.scopes_json = result.scopes
    connection.status = "connected"
    connection.last_verified_at = datetime.now(UTC)
    connection.last_error = None
    db.commit()
    _audit(
        request,
        action="quickbooks_oauth_callback",
        outcome="connected",
        actor=user.email,
        metadata={
            "environment": "sandbox",
            "scope": REQUIRED_SCOPE,
            "realm_id": realm_id,
            "company_name": company.company_name,
        },
    )
    return RedirectResponse(_return_url("connected"), status_code=303)


@router.post("/disconnect", response_model=QuickBooksStatus)
def disconnect_quickbooks(
    payload: QuickBooksDisconnect,
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> QuickBooksStatus:
    _require_admin(user)
    _require_enabled()
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirm the QuickBooks disconnect first.")
    connection = _connection(db)
    if connection is None:
        return _status(db)

    revocation = "not_available"
    token = None
    if connection.encrypted_refresh_token:
        token = decrypt_token(connection.encrypted_refresh_token)
    elif connection.encrypted_access_token:
        token = decrypt_token(connection.encrypted_access_token)
    if token:
        try:
            revoke_token(token)
            revocation = "completed"
        except QuickBooksUnavailable:
            revocation = "provider_unavailable"

    connection.encrypted_access_token = None
    connection.encrypted_refresh_token = None
    connection.token_expires_at = None
    connection.refresh_token_expires_at = None
    connection.status = "disconnected"
    connection.last_error = (
        None
        if revocation == "completed"
        else "Local connection cleared; Intuit token revocation could not be confirmed."
    )
    db.commit()
    _audit(
        request,
        action="quickbooks_disconnect",
        outcome="completed",
        actor=user.email,
        metadata={
            "environment": "sandbox",
            "realm_id": connection.realm_id,
            "revocation": revocation,
        },
    )
    return _status(db)
