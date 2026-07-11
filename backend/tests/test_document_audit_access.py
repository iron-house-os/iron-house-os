import pytest

from app.services.document_audit_access import (
    DocumentAuditPermission,
    can_access_document_audit,
    document_audit_permissions_for_role,
    normalize_role,
    require_document_audit_permission,
)


def test_role_normalization_and_unknown_roles() -> None:
    assert normalize_role(" Operations Manager ") == "operations_manager"
    assert document_audit_permissions_for_role("unknown") == frozenset()


def test_admin_has_all_document_audit_permissions() -> None:
    permissions = document_audit_permissions_for_role("admin")

    assert permissions == frozenset(DocumentAuditPermission)


def test_operations_manager_can_read_and_export_but_not_administer() -> None:
    assert can_access_document_audit("operations_manager", DocumentAuditPermission.READ)
    assert can_access_document_audit("operations manager", DocumentAuditPermission.EXPORT)
    assert not can_access_document_audit(
        "operations_manager", DocumentAuditPermission.ADMINISTER
    )


def test_estimator_is_read_only() -> None:
    assert can_access_document_audit("estimator", DocumentAuditPermission.READ)
    assert not can_access_document_audit("estimator", DocumentAuditPermission.EXPORT)


def test_permission_requirement_raises_for_denied_role() -> None:
    with pytest.raises(PermissionError, match="lacks document audit permission"):
        require_document_audit_permission("viewer", DocumentAuditPermission.READ)
