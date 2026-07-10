from dataclasses import asdict, dataclass
import json
import logging
from uuid import UUID

logger = logging.getLogger("ihos.document_audit")


@dataclass(frozen=True)
class DocumentAuditEvent:
    action: str
    document_id: UUID | None = None
    project_id: UUID | None = None
    outcome: str = "success"


def emit_document_audit_event(event: DocumentAuditEvent) -> None:
    payload = {
        key: str(value) if isinstance(value, UUID) else value
        for key, value in asdict(event).items()
        if value is not None
    }
    logger.info("document_audit %s", json.dumps(payload, sort_keys=True))
