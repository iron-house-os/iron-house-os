from dataclasses import dataclass

from fastapi import HTTPException, status

from app.api.dependencies.auth import CurrentUser

from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.document_audit_access import (
    DocumentAuditPermission,
    document_audit_permissions_for_role,
    normalize_role,
    require_document_audit_permission,
)


@dataclass(frozen=True)
class DocumentAuditPrincipal:
    role: str
    actor: str


def get_document_audit_principal(
    user: CurrentUser,
) -> DocumentAuditPrincipal:
    return DocumentAuditPrincipal(role=normalize_role(user.role), actor=user.email)


def describe_document_audit_access(
    principal: DocumentAuditPrincipal,
) -> dict[str, str | list[str]]:
    permissions = sorted(
        permission.value
        for permission in document_audit_permissions_for_role(principal.role)
    )
    return {
        "role": normalize_role(principal.role),
        "actor": principal.actor,
        "permissions": permissions,
    }


def authorize_document_audit(
    principal: DocumentAuditPrincipal,
    permission: DocumentAuditPermission,
) -> None:
    try:
        require_document_audit_permission(principal.role, permission)
    except PermissionError as exc:
        emit_document_audit_event(
            DocumentAuditEvent(
                action="audit_access",
                outcome="denied",
                actor=principal.actor,
                metadata={"permission": permission.value},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
