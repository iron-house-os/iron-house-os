from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.services.access_control import can_access_module, required_permission
from app.services.auth import AuthenticatedUser, account_to_principal, decode_session_token, get_account
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.request_context import get_request_audit_context


def require_authenticated_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> AuthenticatedUser:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in is required.",
        )
    try:
        claims = decode_session_token(token)
        account_id = UUID(str(claims["sub"]))
        session_version = int(claims["sv"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired.",
        ) from exc
    account = get_account(db, account_id)
    if account is None or not account.is_active or account.session_version != session_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is no longer active.",
        )
    principal = account_to_principal(account)
    request.state.authenticated_user = principal
    return principal


CurrentUser = Annotated[AuthenticatedUser, Depends(require_authenticated_user)]


def require_module_access(request: Request, user: CurrentUser) -> AuthenticatedUser:
    prefix = get_settings().api_v1_prefix.strip("/").split("/")
    path_parts = request.url.path.strip("/").split("/")
    if path_parts[: len(prefix)] != prefix or len(path_parts) <= len(prefix):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested module is not available.",
        )
    module = path_parts[len(prefix)]
    permission = required_permission(module, request.method)
    if user.password_reset_required:
        context = get_request_audit_context(request)
        emit_document_audit_event(
            DocumentAuditEvent(
                action="module_access",
                outcome="denied",
                actor=user.email,
                request_id=context.request_id,
                metadata={
                    "module": module,
                    "method": request.method,
                    "path": request.url.path,
                    "reason": "password_change_required",
                    "role": user.role,
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Change your temporary password before accessing business modules.",
        )
    if can_access_module(user.role, module, permission):
        return user

    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="module_access",
            outcome="denied",
            actor=user.email,
            request_id=context.request_id,
            metadata={
                "module": module,
                "permission": permission.value,
                "method": request.method,
                "path": request.url.path,
                "role": user.role,
            },
        )
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            f"Role '{user.role}' lacks '{permission.value}' permission "
            f"for module '{module}'."
        ),
    )


def require_admin(user: CurrentUser) -> AuthenticatedUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return user


AdminUser = Annotated[AuthenticatedUser, Depends(require_admin)]
