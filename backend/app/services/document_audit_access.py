from enum import StrEnum


class DocumentAuditPermission(StrEnum):
    READ = "read"
    EXPORT = "export"
    ADMINISTER = "administer"


_ROLE_PERMISSIONS: dict[str, frozenset[DocumentAuditPermission]] = {
    "admin": frozenset(DocumentAuditPermission),
    "operations_manager": frozenset(
        {DocumentAuditPermission.READ, DocumentAuditPermission.EXPORT}
    ),
    "estimator": frozenset({DocumentAuditPermission.READ}),
    "viewer": frozenset(),
}


def normalize_role(role: str | None) -> str:
    return (role or "viewer").strip().lower().replace(" ", "_")


def document_audit_permissions_for_role(role: str | None) -> frozenset[DocumentAuditPermission]:
    return _ROLE_PERMISSIONS.get(normalize_role(role), frozenset())


def can_access_document_audit(
    role: str | None,
    permission: DocumentAuditPermission,
) -> bool:
    return permission in document_audit_permissions_for_role(role)


def require_document_audit_permission(
    role: str | None,
    permission: DocumentAuditPermission,
) -> None:
    if not can_access_document_audit(role, permission):
        normalized_role = normalize_role(role)
        raise PermissionError(
            f"Role '{normalized_role}' lacks document audit permission '{permission.value}'"
        )
