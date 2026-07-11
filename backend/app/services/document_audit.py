from collections import Counter, deque
import csv
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from io import StringIO
import json
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("ihos.document_audit")
MAX_RECENT_EVENTS = 200
_recent_events: deque[dict[str, Any]] = deque(maxlen=MAX_RECENT_EVENTS)


@dataclass(frozen=True)
class DocumentAuditEvent:
    action: str
    document_id: UUID | None = None
    project_id: UUID | None = None
    outcome: str = "success"
    actor: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def _serialize(value: Any) -> Any:
    if isinstance(value, (UUID, datetime)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def emit_document_audit_event(event: DocumentAuditEvent) -> None:
    payload = {
        key: _serialize(value)
        for key, value in asdict(event).items()
        if value not in (None, {}, [])
    }
    _recent_events.appendleft(payload)
    logger.info("document_audit %s", json.dumps(payload, sort_keys=True))


def list_recent_document_audit_events(
    limit: int = 50,
    *,
    action: str | None = None,
    outcome: str | None = None,
    actor: str | None = None,
    project_id: UUID | str | None = None,
) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(limit, MAX_RECENT_EVENTS))
    expected_project_id = str(project_id) if project_id is not None else None
    filtered = (
        event
        for event in _recent_events
        if (action is None or event.get("action") == action)
        and (outcome is None or event.get("outcome", "success") == outcome)
        and (actor is None or event.get("actor") == actor)
        and (expected_project_id is None or event.get("project_id") == expected_project_id)
    )
    return list(filtered)[:bounded_limit]


def summarize_document_audit_events() -> dict[str, Any]:
    events = list(_recent_events)
    return {
        "total": len(events),
        "by_action": dict(Counter(event.get("action", "unknown") for event in events)),
        "by_outcome": dict(Counter(event.get("outcome", "success") for event in events)),
    }


def export_document_audit_events_csv(events: list[dict[str, Any]]) -> str:
    output = StringIO()
    fieldnames = [
        "occurred_at",
        "action",
        "outcome",
        "actor",
        "request_id",
        "project_id",
        "document_id",
        "metadata",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for event in events:
        row = dict(event)
        row["metadata"] = json.dumps(row.get("metadata", {}), sort_keys=True)
        writer.writerow(row)
    return output.getvalue()


def clear_recent_document_audit_events() -> None:
    _recent_events.clear()
