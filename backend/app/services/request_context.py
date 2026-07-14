from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request

from app.services.auth import AuthenticatedUser

MAX_REQUEST_ID_LENGTH = 128


@dataclass(frozen=True)
class RequestAuditContext:
    actor: str | None
    request_id: str


def normalize_request_id(value: str | None) -> str:
    if value and len(value) <= MAX_REQUEST_ID_LENGTH and all(
        character.isalnum() or character in "-_.:" for character in value
    ):
        return value
    return f"req-{uuid4().hex}"


def get_request_audit_context(request: Request) -> RequestAuditContext:
    authenticated_user: AuthenticatedUser | None = getattr(
        request.state,
        "authenticated_user",
        None,
    )
    actor = authenticated_user.email if authenticated_user is not None else None
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = normalize_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
    return RequestAuditContext(actor=actor, request_id=request_id)
