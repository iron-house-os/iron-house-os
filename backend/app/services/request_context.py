from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request

from app.services.auth import AuthenticatedUser


@dataclass(frozen=True)
class RequestAuditContext:
    actor: str | None
    request_id: str


def get_request_audit_context(request: Request) -> RequestAuditContext:
    authenticated_user: AuthenticatedUser | None = getattr(
        request.state,
        "authenticated_user",
        None,
    )
    actor = authenticated_user.email if authenticated_user is not None else None
    request_id = request.headers.get("x-request-id") or f"req-{uuid4().hex}"
    return RequestAuditContext(actor=actor, request_id=request_id)
