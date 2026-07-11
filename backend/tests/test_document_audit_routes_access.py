import pytest
from fastapi import HTTPException

from app.api.v1.routes.documents import (
    document_audit_events,
    document_audit_export,
    document_audit_summary,
)
from app.services.document_audit import (
    DocumentAuditEvent,
    clear_recent_document_audit_events,
    emit_document_audit_event,
)
from app.services.document_audit_auth import DocumentAuditPrincipal


def setup_function() -> None:
    clear_recent_document_audit_events()


def test_viewer_cannot_read_audit_events() -> None:
    with pytest.raises(HTTPException) as exc_info:
        document_audit_events(
            DocumentAuditPrincipal(role="viewer"),
            limit=50,
            action=None,
            outcome=None,
            actor=None,
            project_id=None,
        )
    assert exc_info.value.status_code == 403


def test_estimator_can_read_but_cannot_export() -> None:
    principal = DocumentAuditPrincipal(role="estimator")
    emit_document_audit_event(DocumentAuditEvent(action="upload"))

    result = document_audit_events(
        principal,
        limit=50,
        action=None,
        outcome=None,
        actor=None,
        project_id=None,
    )
    assert result["total"] == 1

    with pytest.raises(HTTPException) as exc_info:
        document_audit_export(
            principal,
            limit=200,
            action=None,
            outcome=None,
            actor=None,
            project_id=None,
        )
    assert exc_info.value.status_code == 403


def test_operations_manager_can_export_and_admin_can_summarize() -> None:
    emit_document_audit_event(DocumentAuditEvent(action="upload"))

    response = document_audit_export(
        DocumentAuditPrincipal(role="operations_manager"),
        limit=200,
        action=None,
        outcome=None,
        actor=None,
        project_id=None,
    )
    assert response.media_type == "text/csv"

    summary = document_audit_summary(DocumentAuditPrincipal(role="admin"))
    assert summary["total"] == 1
