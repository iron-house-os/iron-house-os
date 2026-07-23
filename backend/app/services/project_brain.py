import hashlib
import io
import json
import re
import zipfile
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assistant import ProjectMemory

MAX_EXPORT_BYTES = 75 * 1024 * 1024
MAX_CONVERSATION_CHARS = 250_000
PROJECT_MARKERS = (
    "iron house", "ihos", "iron_house_os", "iron-house-os", "rfq", "supplier master",
    "estimate engine", "tender tracker", "municipality intelligence", "build 20", "build 1",
    "build 2", "build 3", "build 4", "build 5", "build 6", "build 7", "build 8", "build 9",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_ -]?key|secret[_ -]?key|password|access[_ -]?token)\s*[:=]\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
)
CANONICAL_MEMORY = (
    ("canonical:identity", "Company identity", 95, "Iron House Civil Constructors operates Iron House OS. Owners named in project planning are Jeremie Peters and Mack Warren. The established OS visual appearance is locked against significant change without Jeremie Peters' explicit approval."),
    ("canonical:execution-model", "Civil execution model", 90, "Default bid execution model: self-perform excavation, trenching, pipe installation, manholes and catch basins, backfill, compaction, subgrade, granular base, topsoil, cleanup and general earthworks. Subcontract concrete formwork and placement, fine grading for asphalt, asphalt paving, pavement markings and street lighting."),
    ("canonical:suppliers", "Default supplier preferences", 90, "Use EMCO for PVC and ductile iron pipe; Amrize for catch basins and manholes; Superior Paving for asphalt; Advanced Testing for testing; JWS for concrete subcontracting; and Performance Coring for coring unless management directs otherwise."),
    ("canonical:portals", "Role-scoped portals", 95, "Employees receive only their own employee, foreman or operator portal. Portal work includes time, schedules, journals, safety, milestones, small equipment, photos, inspections, loads, employee records and role-specific workflows. Company and management modules remain hidden from employee accounts."),
    ("canonical:cost-codes", "Utility cost-code structure", 95, "Cost codes separate storm mains and services, sanitary mains and services, and water mains and services. Shallows separately includes combined hydro and communications plus streetlight installation."),
    ("canonical:field-materials", "Field materials and load tracking", 90, "Foreman material tracking records imports and exports, gravel types, loads and tonnes. Operator portal includes a load tracker."),
    ("canonical:agent-policy", "Iron House agent operating policy", 100, "The embedded agent is management-only, separate from ChatGPT, and must preserve an audit trail. Deployed code and database state outrank merged build records, explicit management decisions, newer chats and older discussions. Consequential writes, merges, deployments, financial approvals, deletions and external messages require a preview and explicit management confirmation."),
)


def seed_canonical_memory(db: Session) -> None:
    changed = False
    for source_id, title, authority, content in CANONICAL_MEMORY:
        if db.scalar(select(ProjectMemory.id).where(ProjectMemory.source_id == source_id)) is None:
            db.add(ProjectMemory(source_kind="management_decision", source_id=source_id, title=title,
                                 content=content, authority=authority, imported_by="Build 229 canonical seed"))
            changed = True
    if changed:
        db.commit()


def memory_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(ProjectMemory)) or 0)


def import_chatgpt_export(db: Session, raw: bytes, filename: str, actor: str) -> dict[str, int]:
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError("The export is larger than the 75 MB import limit.")
    payload = _load_export(raw, filename)
    conversations = payload if isinstance(payload, list) else payload.get("conversations", [])
    if not isinstance(conversations, list):
        raise ValueError("No ChatGPT conversations were found in the export.")
    imported = updated = skipped = 0
    for conversation in conversations:
        parsed = _parse_conversation(conversation)
        if parsed is None:
            skipped += 1
            continue
        source_id, title, content, source_date = parsed
        existing = db.scalar(select(ProjectMemory).where(ProjectMemory.source_id == source_id))
        if existing:
            existing.title, existing.content, existing.source_date = title, content, source_date
            existing.imported_by = actor
            updated += 1
        else:
            db.add(ProjectMemory(source_kind="chatgpt_conversation", source_id=source_id, title=title,
                                 content=content, authority=60, source_date=source_date,
                                 source_url=None, imported_by=actor))
            imported += 1
    db.commit()
    return {"imported": imported, "updated": updated, "skipped": skipped,
            "total_project_memories": memory_count(db)}


def search_memory(
    db: Session,
    query: str = "",
    source_kind: str | None = None,
    min_authority: int = 0,
    limit: int = 25,
) -> list[ProjectMemory]:
    """Return authority-ranked Project Brain records with deterministic text scoring."""
    statement = select(ProjectMemory).where(ProjectMemory.authority >= min_authority)
    if source_kind:
        statement = statement.where(ProjectMemory.source_kind == source_kind)
    candidates = list(db.scalars(statement.order_by(
        ProjectMemory.authority.desc(), ProjectMemory.source_date.desc()
    ).limit(500)))
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9-]{2,}", query)}
    phrase = query.strip().lower()

    def score(item: ProjectMemory) -> tuple[int, int, float]:
        title = item.title.lower()
        content = item.content.lower()
        title_hits = sum(20 for term in terms if term in title)
        content_hits = sum(7 for term in terms if term in content)
        phrase_bonus = 40 if phrase and (phrase in title or phrase in content) else 0
        source_bonus = 15 if item.source_kind == "management_decision" else 0
        timestamp = item.source_date.timestamp() if item.source_date else 0.0
        return (item.authority + title_hits + content_hits + phrase_bonus + source_bonus,
                item.authority, timestamp)

    if not terms and not phrase:
        return candidates[:limit]
    return sorted(candidates, key=score, reverse=True)[:limit]


def relevant_memory(db: Session, query: str, limit: int = 10) -> list[ProjectMemory]:
    return search_memory(db, query=query, min_authority=0, limit=limit)


def format_memory_context(items: list[ProjectMemory]) -> str:
    if not items:
        return "No Project Brain records matched this request."
    return "\n\n".join(
        f"[Project Brain | authority {item.authority} | {item.source_kind} | {item.title}]\n{item.content[:6000]}"
        for item in items
    )


def _load_export(raw: bytes, filename: str) -> Any:
    if filename.lower().endswith(".zip") or raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = [name for name in archive.namelist() if re.search(r"(^|/)conversations(?:-\d+)?\.json$", name)]
            if not names:
                raise ValueError("The ZIP does not contain conversations.json.")
            if sum(archive.getinfo(name).file_size for name in names) > MAX_EXPORT_BYTES:
                raise ValueError("The uncompressed conversation history is larger than the 75 MB import limit.")
            combined: list[Any] = []
            for name in names:
                value = json.loads(archive.read(name))
                combined.extend(value if isinstance(value, list) else value.get("conversations", []))
            return combined
    return json.loads(raw.decode("utf-8"))


def _parse_conversation(value: Any) -> tuple[str, str, str, datetime | None] | None:
    if not isinstance(value, dict):
        return None
    title = str(value.get("title") or "Untitled ChatGPT conversation")[:255]
    messages: list[tuple[float, str]] = []
    for node in (value.get("mapping") or {}).values():
        message = node.get("message") if isinstance(node, dict) else None
        if not isinstance(message, dict):
            continue
        author = str((message.get("author") or {}).get("role") or "unknown")
        parts = (message.get("content") or {}).get("parts") or []
        text = "\n".join(part for part in parts if isinstance(part, str)).strip()
        if text:
            messages.append((float(message.get("create_time") or 0), f"{author.upper()}: {_redact(text)}"))
    messages.sort(key=lambda item: item[0])
    content = "\n\n".join(text for _, text in messages)[:MAX_CONVERSATION_CHARS]
    searchable = f"{title}\n{content[:30000]}".lower()
    if not any(marker in searchable for marker in PROJECT_MARKERS):
        return None
    fallback_id = hashlib.sha256(f"{title}\n{content[:500]}".encode()).hexdigest()
    external_id = str(value.get("id") or value.get("conversation_id") or fallback_id)
    timestamp = value.get("create_time")
    source_date = datetime.fromtimestamp(float(timestamp), UTC) if timestamp else None
    return f"chatgpt:{external_id}", title, content, source_date


def _redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED SECRET]", text)
    return text
