from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import UserAccount
from app.schemas.auth import AuthStatus, LoginRequest, UserAccountRead
from app.services.auth import authenticate, create_session_token

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
def login(payload: LoginRequest, response: Response, db: DBSession) -> AuthStatus:
    account = authenticate(db, str(payload.email), payload.password)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
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
