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
    describe_document_audit_access,
    get_document_audit_principal,
)
from app.services.auth import AuthenticatedUser
from uuid import UUID


def setup_function() -> None:
    clear_recent_document_audit_events()


def test_principal_uses_authenticated_role_and_email() -> None:
    user = AuthenticatedUser(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="jeremie@ironhousecontracting.com",
        display_name="Jeremie Peters",
        role="operations_manager",
        session_version=1,
    )
    principal = get_document_audit_principal(user)
    assert principal == DocumentAuditPrincipal(
        role="operations_manager",
        actor="jeremie@ironhousecontracting.com",
    )


def test_permission_snapshots_are_normalized_and_sorted() -> None:
    assert describe_document_audit_access(DocumentAuditPrincipal(role="Admin", actor="admin@example.com")) == {
        "role": "admin",
        "actor": "admin@example.com",
        "permissions": ["administer", "export", "read"],
    }
    assert describe_document_audit_access(
        DocumentAuditPrincipal(role="operations manager", actor="ops@example.com")
    ) == {
        "role": "operations_manager",
        "actor": "ops@example.com",
        "permissions": ["export", "read"],
    }
    assert describe_document_audit_access(DocumentAuditPrincipal(role="estimator", actor="est@example.com")) == {
        "role": "estimator",
        "actor": "est@example.com",
        "permissions": ["read"],
    }
    assert describe_document_audit_access(DocumentAuditPrincipal(role="viewer", actor="view@example.com")) == {
        "role": "viewer",
        "actor": "view@example.com",
        "permissions": [],
    }


def test_authorize_allows_role_permission_without_denial_event() -> None:
    authorize_document_audit(
        DocumentAuditPrincipal(role="operations_manager", actor="ops@example.com"),
        DocumentAuditPermission.EXPORT,
    )
    assert list_recent_document_audit_events() == []


def test_authorize_rejects_and_audits_missing_permission() -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_document_audit(
            DocumentAuditPrincipal(role="viewer", actor="viewer@example.com"),
            DocumentAuditPermission.READ,
        )

    assert exc_info.value.status_code == 403
    assert "lacks document audit permission 'read'" in str(exc_info.value.detail)
    assert list_recent_document_audit_events() == [
        {
            "action": "audit_access",
            "outcome": "denied",
            "actor": "viewer@example.com",
            "metadata": {"permission": "read"},
            "occurred_at": list_recent_document_audit_events()[0]["occurred_at"],
        }
    ]
