from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.services.auth import AuthenticatedUser, account_to_principal, decode_session_token, get_account


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


def require_admin(user: CurrentUser) -> AuthenticatedUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return user


AdminUser = Annotated[AuthenticatedUser, Depends(require_admin)]
