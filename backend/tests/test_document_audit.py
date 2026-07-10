import json
import logging
from uuid import uuid4

from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event


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
