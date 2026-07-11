import pytest
from fastapi import HTTPException

from app.services.document_audit import (
    clear_recent_document_audit_events,
    list_recent_document_audit_events,
)
from app.services.document_audit_access import DocumentAuditPermission
from app.services.document_audit_auth import (
    DocumentAuditPrincipal,
    authorize_document_audit,
    get_document_audit_principal,
)


def setup_function() -> None:
    clear_recent_document_audit_events()


def test_principal_normalizes_header_role() -> None:
    principal = get_document_audit_principal(" Operations Manager ")
    assert principal == DocumentAuditPrincipal(role="operations_manager")


def test_authorize_allows_role_permission_without_denial_event() -> None:
    authorize_document_audit(
        DocumentAuditPrincipal(role="operations_manager"),
        DocumentAuditPermission.EXPORT,
    )
    assert list_recent_document_audit_events() == []


def test_authorize_rejects_and_audits_missing_permission() -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_document_audit(
            DocumentAuditPrincipal(role="viewer"),
            DocumentAuditPermission.READ,
        )

    assert exc_info.value.status_code == 403
    assert "lacks document audit permission 'read'" in str(exc_info.value.detail)
    assert list_recent_document_audit_events() == [
        {
            "action": "audit_access",
            "outcome": "denied",
            "actor": "viewer",
            "metadata": {"permission": "read"},
            "occurred_at": list_recent_document_audit_events()[0]["occurred_at"],
        }
    ]
