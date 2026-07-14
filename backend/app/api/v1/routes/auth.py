from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import UserAccount
from app.schemas.auth import (
    AuthStatus,
    LoginRequest,
    PasswordChangeRequest,
    RoleAccessRead,
    UserAccountRead,
)
from app.services import auth
from app.services.access_control import describe_role_access
from app.services.auth import AuthenticationStatus, authenticate, create_session_token
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.request_context import get_request_audit_context

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = int(timedelta(minutes=settings.access_token_expire_minutes).total_seconds())
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("")
def auth_capability() -> dict[str, str]:
    return {
        "authentication": "session",
        "message": "Sign in with an Iron House OS user account.",
    }


@router.post("/login", response_model=AuthStatus, status_code=status.HTTP_200_OK)
def login(payload: LoginRequest, request: Request, response: Response, db: DBSession) -> AuthStatus:
    result = authenticate(db, str(payload.email), payload.password)
    context = get_request_audit_context(request)
    if result.status == AuthenticationStatus.LOCKED:
        retry_after = max(
            1,
            int(((result.locked_until or datetime.now(UTC)) - datetime.now(UTC)).total_seconds()),
        )
        emit_document_audit_event(
            DocumentAuditEvent(
                action="login",
                outcome="locked",
                request_id=context.request_id,
                metadata={"subject_hash": result.subject_hash},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Sign-in is temporarily unavailable. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    if result.status != AuthenticationStatus.AUTHENTICATED or result.account is None:
        emit_document_audit_event(
            DocumentAuditEvent(
                action="login",
                outcome="denied",
                request_id=context.request_id,
                metadata={"subject_hash": result.subject_hash},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    account = result.account
    emit_document_audit_event(
        DocumentAuditEvent(
            action="login",
            actor=account.email,
            request_id=context.request_id,
            metadata={"subject_hash": result.subject_hash},
        )
    )
    _set_session_cookie(response, create_session_token(account))
    return AuthStatus(authentication="authenticated", user=UserAccountRead.model_validate(account))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/me", response_model=AuthStatus)
def current_account(user: CurrentUser, db: DBSession) -> AuthStatus:
    account = db.get(UserAccount, user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found.")
    return AuthStatus(authentication="authenticated", user=UserAccountRead.model_validate(account))


@router.get("/me/permissions", response_model=RoleAccessRead)
def current_permissions(user: CurrentUser) -> RoleAccessRead:
    return RoleAccessRead(role=user.role, modules=describe_role_access(user.role))


@router.post("/change-password", response_model=AuthStatus)
def change_current_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    user: CurrentUser,
    db: DBSession,
) -> AuthStatus:
    account = db.get(UserAccount, user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found.")
    context = get_request_audit_context(request)
    try:
        account = auth.change_password(
            db,
            account,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        emit_document_audit_event(
            DocumentAuditEvent(
                action="password_change",
                outcome="denied",
                actor=user.email,
                request_id=context.request_id,
            )
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    emit_document_audit_event(
        DocumentAuditEvent(
            action="password_change",
            actor=account.email,
            request_id=context.request_id,
        )
    )
    _set_session_cookie(response, create_session_token(account))
    return AuthStatus(authentication="authenticated", user=UserAccountRead.model_validate(account))
