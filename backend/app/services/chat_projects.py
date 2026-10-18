"""Narrow, source-linked project operations for the authenticated chat connector."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from uuid import uuid5, NAMESPACE_URL

from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.project import Project
from app.models.user import UserAccount
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event


class TenderIntake(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_folder_id: str = Field(pattern=r"^[A-Za-z0-9_-]{10,200}$")
    name: str = Field(min_length=1, max_length=255)
    tender_number: str | None = Field(default=None, max_length=120)
    municipality: str | None = Field(default=None, max_length=255)
    client_owner: str | None = Field(default=None, max_length=255)
    project_address: str | None = Field(default=None, max_length=500)
    aliases: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip() or "release smoke" in value.casefold() or value.upper().startswith("IHCC-TEST"):
            raise ValueError("A real tender project name is required")
        return value.strip()


def require_manager(account: UserAccount | None) -> UserAccount:
    if (account is None or not account.is_active or account.password_reset_required
            or account.role != "admin"):
        raise PermissionError("Active IHOS administrator access is required")
    return account


def normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def source_key(item: TenderIntake) -> str:
    return "drive-tender:" + item.source_folder_id


def summary(project: Project) -> dict:
    return {"id": str(project.id), "name": project.name, "status": project.status,
            "project_number": project.project_number, "tender_number": project.tender_number,
            "deleted": project.deleted_at is not None,
            "source_import_key": (project.metadata_json or {}).get("source_import_key"),
            "source_folder": (project.metadata_json or {}).get("source_folder"),
            "path": f"/projects/{project.id}"}


def plan_intake(db: Session, item: TenderIntake) -> dict:
    projects = db.scalars(select(Project)).all()  # Includes Trash to prevent resurrection/duplication.
    key = source_key(item)
    names = {normalized(item.name), *(normalized(alias) for alias in item.aliases)}
    matches = [project for project in projects if (
        (project.metadata_json or {}).get("source_import_key") == key
        or normalized(project.name) in names
        or (item.tender_number and normalized(project.tender_number) == normalized(item.tender_number))
    )]
    if len(matches) > 1 or any(project.deleted_at is not None for project in matches):
        return {"action": "conflict", "matches": [summary(project) for project in matches]}
    if matches:
        project = matches[0]
        previous_key = (project.metadata_json or {}).get("source_import_key")
        # Name/number matches are candidates, never silently treated as proof of identity.
        if previous_key != key:
            return {"action": "conflict", "matches": [summary(project)],
                    "reason": "Existing project requires exact source-folder reconciliation in IHOS"}
        evidence = (project.metadata_json or {}).get("chat_tender_intake", {})
        if evidence.get("payload") != item.model_dump(mode="json"):
            return {"action": "conflict", "matches": [summary(project)], "reason": "Source content changed"}
        return {"action": "reuse", "project": summary(project)}
    return {"action": "create", "name": item.name, "status": "opportunity", "project_number": None}


def preview_intake(db: Session, account: UserAccount, item: TenderIntake) -> dict:
    require_manager(account)
    plan = plan_intake(db, item)
    if plan["action"] == "conflict":
        return plan
    claims = {"sub": str(account.id), "sv": account.session_version,
              "aud": "ihos-chat-project-preview", "iss": "ihos-chat-connector",
              "exp": datetime.now(UTC) + timedelta(minutes=10),
              "payload": item.model_dump(mode="json"), "plan": plan}
    token = jwt.encode(claims, get_settings().secret_key, algorithm="HS256")
    return {**plan, "preview_token": token, "expires_in": 600,
            "source_folder": f"https://drive.google.com/drive/folders/{item.source_folder_id}"}


def apply_intake(db: Session, account: UserAccount, preview_token: str) -> dict:
    require_manager(account)
    try:
        claims = jwt.decode(preview_token, get_settings().secret_key, algorithms=["HS256"],
                            audience="ihos-chat-project-preview", issuer="ihos-chat-connector")
        if claims["sub"] != str(account.id) or claims["sv"] != account.session_version:
            raise ValueError("Preview identity changed")
        item = TenderIntake.model_validate(claims["payload"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Preview is invalid or expired; request a fresh preview") from exc
    if db.bind is None:
        raise RuntimeError("Database is unavailable")
    if db.bind.dialect.name == "postgresql":
        # Also conflicts with ordinary project inserts/updates, so alias checks and creation are atomic.
        db.execute(text("LOCK TABLE projects IN SHARE ROW EXCLUSIVE MODE"))
    elif get_settings().environment == "production":
        raise RuntimeError("Production connector writes require PostgreSQL locking")
    current = plan_intake(db, item)
    if current["action"] == "reuse":
        return {"operation": "verified_existing", **current["project"]}
    if current != claims["plan"] or current["action"] != "create":
        raise ValueError("Project inventory changed; review a fresh preview")
    payload = item.model_dump(mode="json")
    digest = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    project = Project(id=uuid5(NAMESPACE_URL, source_key(item)), name=item.name,
                      client_owner=item.client_owner, municipality_name=item.municipality,
                      project_address=item.project_address, tender_number=item.tender_number,
                      status="opportunity", project_number=None,
                      metadata_json={"source_import_key": source_key(item),
                                     "source_folder": f"https://drive.google.com/drive/folders/{item.source_folder_id}",
                                     "chat_tender_intake": {"payload": payload, "digest": digest,
                                                            "actor_id": str(account.id),
                                                            "created_at": datetime.now(UTC).isoformat()}})
    db.add(project)
    db.flush()
    # Fail the transaction if the audit store rejects the event.
    emit_document_audit_event(DocumentAuditEvent(action="chat_tender_intake", project_id=project.id,
                                               actor=account.email, metadata={"source_key": source_key(item)}))
    db.commit()
    db.refresh(project)
    return {"operation": "created", **summary(project)}


def project_inventory(db: Session, account: UserAccount, offset: int = 0, limit: int = 50) -> dict:
    require_manager(account)
    if offset < 0 or not 1 <= limit <= 100:
        raise ValueError("Use nonnegative offset and limit between 1 and 100")
    rows = db.scalars(select(Project).order_by(Project.id).offset(offset).limit(limit + 1)).all()
    return {"items": [summary(project) for project in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None}
