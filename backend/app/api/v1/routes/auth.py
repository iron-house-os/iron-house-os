from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class AuthStatus(BaseModel):
    authentication: str
    message: str


@router.get("", response_model=AuthStatus, status_code=status.HTTP_200_OK)
def auth_status() -> AuthStatus:
    return AuthStatus(
        authentication="scaffold",
        message="Authentication routes are reserved for Phase 2 implementation.",
    )
