from datetime import UTC, datetime, timedelta
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.core.errors import quickbooks_oauth_redirect
from app.db.session import get_db
from app.models.quickbooks import (
    QuickBooksConfiguration,
    QuickBooksConnection,
    QuickBooksOAuthState,
)
from app.schemas.quickbooks import (
    QuickBooksAuthorization,
    QuickBooksConfigurationRemove,
    QuickBooksConfigurationWrite,
    QuickBooksDisconnect,
    QuickBooksStatus,
)
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.quickbooks import (
    REQUIRED_SCOPE,
    QuickBooksUnavailable,
    QuickBooksCredentials,
    authorization_url,
    decrypt_configuration_secret,
    decrypt_token,
    encrypt_token,
    encrypt_configuration_secret,
    environment_credentials,
    exchange_authorization_code,
    get_company_info,
    live_read_only_is_approved,
    quickbooks_environment,
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


def _environment() -> str:
    try:
        return quickbooks_environment()
    except QuickBooksUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _environment_label(environment: str) -> str:
    return "live read-only" if environment == "production" else "sandbox"


def _require_environment_approved() -> str:
    environment = _environment()
    if not live_read_only_is_approved(environment):
        raise HTTPException(
            status_code=503,
            detail="QuickBooks live read-only connection is awaiting owner approval.",
        )
    return environment


def _require_enabled(db: Session) -> None:
    environment = _require_environment_approved()
    if not _feature_enabled(db):
        raise HTTPException(
            status_code=503,
            detail=f"QuickBooks {_environment_label(environment)} connection is disabled.",
        )


def _connection(db: Session) -> QuickBooksConnection | None:
    return db.scalar(
        select(QuickBooksConnection).where(
            QuickBooksConnection.environment == _environment()
        )
    )


def _stored_configuration(db: Session) -> QuickBooksConfiguration | None:
    return db.scalar(
        select(QuickBooksConfiguration).where(
            QuickBooksConfiguration.environment == _environment(),
        )
    )


def _configuration(db: Session) -> QuickBooksConfiguration | None:
    configuration = _stored_configuration(db)
    return configuration if configuration and configuration.enabled else None


def _feature_enabled(db: Session) -> bool:
    settings = get_settings()
    if settings.quickbooks_force_disabled:
        return False
    if not live_read_only_is_approved(_environment()):
        return False
    return bool(settings.quickbooks_enabled or _configuration(db))


def _credentials(db: Session) -> QuickBooksCredentials | None:
    configuration = _configuration(db)
    if configuration is not None:
        return QuickBooksCredentials(
            client_id=configuration.client_id,
            client_secret=decrypt_configuration_secret(configuration.encrypted_client_secret),
            token_encryption_key=decrypt_configuration_secret(
                configuration.encrypted_token_encryption_key
            ),
        )
    return environment_credentials()


def _consume_oauth_state(db: Session, *, state: str, owner_account_id: UUID) -> bool:
    """Atomically consume one valid state so concurrent callbacks cannot reuse it."""
    now = datetime.now(UTC)
    result = db.execute(
        update(QuickBooksOAuthState)
        .where(
            QuickBooksOAuthState.state_digest == state_digest(state),
            QuickBooksOAuthState.owner_account_id == owner_account_id,
            QuickBooksOAuthState.environment == _environment(),
            QuickBooksOAuthState.used_at.is_(None),
            QuickBooksOAuthState.expires_at > now,
        )
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        return False
    db.commit()
    return True


def _status(db: Session) -> QuickBooksStatus:
    environment = _environment()
    database_configured = _stored_configuration(db) is not None
    configuration_error = None
    try:
        credentials = _credentials(db)
    except QuickBooksUnavailable as exc:
        credentials = None
        configuration_error = str(exc)
    connection = _connection(db)
    connected = bool(
        connection
        and connection.status == "connected"
        and connection.encrypted_refresh_token
        and REQUIRED_SCOPE in connection.scopes_json
    )
    return QuickBooksStatus(
        enabled=_feature_enabled(db),
        configured=credentials is not None and quickbooks_is_configured(credentials),
        database_configured=database_configured,
        connected=connected,
        status=connection.status if connection else "not_connected",
        environment=environment,
        live_read_only_approved=live_read_only_is_approved(environment),
        required_scope=REQUIRED_SCOPE,
        realm_id=connection.realm_id if connection else None,
        company_name=connection.company_name if connection else None,
        legal_name=connection.legal_name if connection else None,
        last_verified_at=connection.last_verified_at if connection else None,
        last_error=(connection.last_error if connection else None) or configuration_error,
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


@router.get("/status", response_model=QuickBooksStatus)
def quickbooks_status(user: CurrentUser, db: DBSession) -> QuickBooksStatus:
    _require_admin(user)
    return _status(db)


@router.put("/configuration", response_model=QuickBooksStatus)
def configure_quickbooks(
    payload: QuickBooksConfigurationWrite,
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> QuickBooksStatus:
    _require_admin(user)
    environment = _require_environment_approved()
    label = _environment_label(environment)
    if not payload.environment_confirmed:
        raise HTTPException(
            status_code=400,
            detail=f"Confirm {label} configuration first.",
        )
    connection = _connection(db)
    if connection and connection.status == "connected":
        raise HTTPException(status_code=409, detail="Disconnect QuickBooks before changing credentials.")

    client_id = payload.client_id.strip()
    client_secret = payload.client_secret.get_secret_value().strip()
    if not (10 <= len(client_id) <= 255) or not (12 <= len(client_secret) <= 1000):
        raise HTTPException(
            status_code=422,
            detail="Enter valid Intuit QuickBooks credentials.",
        )

    configuration = _stored_configuration(db)
    if configuration is None:
        configuration = QuickBooksConfiguration(
            environment=environment,
            configured_by_account_id=user.id,
            client_id=client_id,
            encrypted_client_secret=encrypt_configuration_secret(client_secret),
            encrypted_token_encryption_key=encrypt_configuration_secret(
                secrets.token_urlsafe(48)
            ),
            enabled=True,
        )
        db.add(configuration)
    else:
        configuration.configured_by_account_id = user.id
        configuration.client_id = client_id
        configuration.encrypted_client_secret = encrypt_configuration_secret(client_secret)
        configuration.encrypted_token_encryption_key = encrypt_configuration_secret(
            secrets.token_urlsafe(48)
        )
        configuration.enabled = True
    db.commit()
    _audit(
        request,
        action="quickbooks_configuration",
        outcome="saved",
        actor=user.email,
        metadata={"environment": environment},
    )
    return _status(db)


@router.delete("/configuration", response_model=QuickBooksStatus)
def remove_quickbooks_configuration(
    payload: QuickBooksConfigurationRemove,
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> QuickBooksStatus:
    _require_admin(user)
    environment = _environment()
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirm credential removal first.")
    connection = _connection(db)
    if connection and connection.status == "connected":
        raise HTTPException(status_code=409, detail="Disconnect QuickBooks before removing credentials.")
    db.execute(
        delete(QuickBooksConfiguration).where(
            QuickBooksConfiguration.environment == environment
        )
    )
    db.commit()
    _audit(
        request,
        action="quickbooks_configuration",
        outcome="removed",
        actor=user.email,
        metadata={"environment": environment},
    )
    return _status(db)


@router.post("/oauth/start", response_model=QuickBooksAuthorization)
def start_quickbooks_oauth(
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> QuickBooksAuthorization:
    _require_admin(user)
    _require_enabled(db)
    environment = _environment()
    try:
        credentials = _credentials(db)
    except QuickBooksUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "QuickBooks credentials are unavailable. "
                "Replace or remove the saved credentials."
            ),
        ) from exc
    if not quickbooks_is_configured(credentials):
        raise HTTPException(status_code=503, detail="QuickBooks OAuth is not configured.")
    state = secrets.token_urlsafe(48)
    db.add(
        QuickBooksOAuthState(
            state_digest=state_digest(state),
            owner_account_id=user.id,
            environment=environment,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    db.commit()
    _audit(
        request,
        action="quickbooks_oauth_start",
        outcome="started",
        actor=user.email,
        metadata={"environment": environment, "scope": REQUIRED_SCOPE},
    )
    return QuickBooksAuthorization(authorization_url=authorization_url(state, credentials))


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
    _require_enabled(db)
    environment = _environment()
    credentials = _credentials(db)
    if credentials is None:
        return quickbooks_oauth_redirect("failed")
    if not _consume_oauth_state(db, state=state, owner_account_id=user.id):
        _audit(
            request,
            action="quickbooks_oauth_callback",
            outcome="failed",
            actor=user.email,
            metadata={"environment": environment, "reason": "invalid_or_expired_state"},
        )
        return quickbooks_oauth_redirect("failed")

    if error:
        _audit(
            request,
            action="quickbooks_oauth_callback",
            outcome="denied",
            actor=user.email,
            metadata={"environment": environment, "provider_error": error[:100]},
        )
        return quickbooks_oauth_redirect("denied")
    if not code or not realm_id:
        _audit(
            request,
            action="quickbooks_oauth_callback",
            outcome="failed",
            actor=user.email,
            metadata={"environment": environment, "reason": "incomplete_response"},
        )
        return quickbooks_oauth_redirect("failed")

    connection = _connection(db)
    if connection and connection.status == "connected" and connection.realm_id != realm_id:
        _audit(
            request,
            action="quickbooks_oauth_callback",
            outcome="failed",
            actor=user.email,
            metadata={"environment": environment, "reason": "realm_mismatch"},
        )
        return quickbooks_oauth_redirect("failed")
    try:
        existing_refresh = None
        if connection and connection.encrypted_refresh_token:
            existing_refresh = decrypt_token(
                connection.encrypted_refresh_token,
                credentials.token_encryption_key,
            )
        result = exchange_authorization_code(code, existing_refresh, credentials)
        if not result.refresh_token:
            raise QuickBooksUnavailable("QuickBooks returned no refresh token.")
        company = get_company_info(result.access_token, realm_id, environment)
    except QuickBooksUnavailable as exc:
        if connection:
            connection.last_error = str(exc)[:500]
            db.commit()
        _audit(
            request,
            action="quickbooks_oauth_callback",
            outcome="failed",
            actor=user.email,
            metadata={"environment": environment, "reason": "provider_rejected"},
        )
        return quickbooks_oauth_redirect("failed")

    if connection is None:
        connection = QuickBooksConnection(
            environment=environment,
            connected_by_account_id=user.id,
            realm_id=realm_id,
            company_name=company.company_name,
        )
        db.add(connection)
    connection.connected_by_account_id = user.id
    connection.realm_id = realm_id
    connection.company_name = company.company_name
    connection.legal_name = company.legal_name
    connection.encrypted_access_token = encrypt_token(
        result.access_token,
        credentials.token_encryption_key,
    )
    connection.encrypted_refresh_token = encrypt_token(
        result.refresh_token,
        credentials.token_encryption_key,
    )
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
            "environment": environment,
            "scope": REQUIRED_SCOPE,
            "realm_id": realm_id,
            "company_name": company.company_name,
        },
    )
    return quickbooks_oauth_redirect("connected")


@router.post("/disconnect", response_model=QuickBooksStatus)
def disconnect_quickbooks(
    payload: QuickBooksDisconnect,
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> QuickBooksStatus:
    _require_admin(user)
    environment = _environment()
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirm the QuickBooks disconnect first.")
    connection = _connection(db)
    if connection is None:
        return _status(db)

    revocation = "not_available"
    token = None
    try:
        credentials = _credentials(db)
        if connection.encrypted_refresh_token:
            token = decrypt_token(
                connection.encrypted_refresh_token,
                credentials.token_encryption_key if credentials else None,
            )
        elif connection.encrypted_access_token:
            token = decrypt_token(
                connection.encrypted_access_token,
                credentials.token_encryption_key if credentials else None,
            )
    except QuickBooksUnavailable:
        credentials = None
        revocation = "decryption_failed"
    else:
        if token:
            try:
                revoke_token(token, credentials)
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
            "environment": environment,
            "realm_id": connection.realm_id,
            "revocation": revocation,
        },
    )
    return _status(db)
