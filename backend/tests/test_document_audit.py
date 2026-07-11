import json
import logging
from uuid import uuid4

from app.services.document_audit import (
    DocumentAuditEvent,
    clear_recent_document_audit_events,
    emit_document_audit_event,
    list_recent_document_audit_events,
    summarize_document_audit_events,
)


def test_document_audit_event_serializes_context(caplog) -> None:
    document_id = uuid4()
    project_id = uuid4()

    with caplog.at_level(logging.INFO, logger="ihos.document_audit"):
        emit_document_audit_event(
            DocumentAuditEvent(
                action="document.downloaded",
                document_id=document_id,
                project_id=project_id,
                actor="user@example.com",
                request_id="req-123",
                metadata={"size_bytes": 42, "tags": ["rfq", "current"]},
            )
        )

    message = caplog.records[-1].getMessage()
    payload = json.loads(message.removeprefix("document_audit "))

    assert payload["action"] == "document.downloaded"
    assert payload["document_id"] == str(document_id)
    assert payload["project_id"] == str(project_id)
    assert payload["actor"] == "user@example.com"
    assert payload["request_id"] == "req-123"
    assert payload["metadata"] == {"size_bytes": 42, "tags": ["rfq", "current"]}
    assert payload["occurred_at"].endswith("+00:00")


def test_recent_document_audit_events_support_filters() -> None:
    clear_recent_document_audit_events()
    project_id = uuid4()
    emit_document_audit_event(
        DocumentAuditEvent(action="upload", project_id=project_id, actor="jeremie", outcome="success")
    )
    emit_document_audit_event(
        DocumentAuditEvent(action="signed_download", actor="supplier", outcome="denied")
    )

    assert len(list_recent_document_audit_events(action="upload")) == 1
    assert len(list_recent_document_audit_events(outcome="denied")) == 1
    assert len(list_recent_document_audit_events(actor="jeremie")) == 1
    assert len(list_recent_document_audit_events(project_id=project_id)) == 1
    assert list_recent_document_audit_events(action="missing") == []


def test_document_audit_summary_counts_actions_and_outcomes() -> None:
    clear_recent_document_audit_events()
    emit_document_audit_event(DocumentAuditEvent(action="upload"))
    emit_document_audit_event(DocumentAuditEvent(action="upload"))
    emit_document_audit_event(DocumentAuditEvent(action="signed_download", outcome="denied"))

    summary = summarize_document_audit_events()

    assert summary["total"] == 3
    assert summary["by_action"] == {"upload": 2, "signed_download": 1}
    assert summary["by_outcome"] == {"success": 2, "denied": 1}
