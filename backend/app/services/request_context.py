from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request


@dataclass(frozen=True)
class RequestAuditContext:
    actor: str | None
    request_id: str


def get_request_audit_context(request: Request) -> RequestAuditContext:
    actor = request.headers.get("x-ihos-actor") or request.headers.get("x-forwarded-user")
    request_id = request.headers.get("x-request-id") or f"req-{uuid4().hex}"
    return RequestAuditContext(actor=actor, request_id=request_id)
