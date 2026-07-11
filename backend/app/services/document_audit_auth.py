from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.services.document_audit_access import (
    DocumentAuditPermission,
    normalize_role,
    require_document_audit_permission,
)


@dataclass(frozen=True)
class DocumentAuditPrincipal:
    role: str


def get_document_audit_principal(
    x_ihos_role: str | None = Header(default=None, alias="X-IHOS-Role"),
) -> DocumentAuditPrincipal:
    return DocumentAuditPrincipal(role=normalize_role(x_ihos_role))


def authorize_document_audit(
    principal: DocumentAuditPrincipal,
    permission: DocumentAuditPermission,
) -> None:
    try:
        require_document_audit_permission(principal.role, permission)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
