"""Staging-only, idempotent import of non-secret Google Drive tender metadata.

The importer stores links and metadata only. It never receives Drive credentials,
downloads a source file, or mutates Drive. Dry-run is the default at the command
layer; applying is restricted to an explicit staging invocation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from app.models.document import Document
from app.models.project import Project
from sqlalchemy import select
from sqlalchemy.orm import Session

SOURCE_KEY = "drive_tender_import"
DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/{}"
_DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{10,}$")


class ImportValidationError(ValueError):
    """Raised when the checked-in metadata manifest is unsafe or malformed."""


@dataclass(frozen=True)
class DriveFile:
    drive_file_id: str
    name: str
    mime_type: str
    url: str
    created_time: str | None = None
    modified_time: str | None = None
    source_path: str | None = None


@dataclass(frozen=True)
class TenderFolder:
    drive_folder_id: str
    name: str
    url: str
    files: tuple[DriveFile | Mapping[str, str], ...] = ()


@dataclass(frozen=True)
class ImportDecision:
    action: str
    canonical_name: str
    source_folder_ids: tuple[str, ...]
    reason: str
    reference: str | None = None
    files: tuple[DriveFile, ...] = field(default=(), compare=False, repr=False)
    folders: tuple[TenderFolder, ...] = field(default=(), compare=False, repr=False)


def normalize_tender_name(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    replacements = {
        "sani": "sanitary",
        "voc": "village of cumberland",
        "itt": "",
    }
    tokens = [replacements.get(token, token) for token in value.split()]
    return " ".join(token for token in tokens if token)


def extract_reference(value: str) -> str | None:
    references = extract_references(value)
    return references[0] if references else None


def extract_references(value: str) -> tuple[str, ...]:
    patterns = (
        r"\bITT[- _]?\d{3,}\b",
        r"\bQ\d{2}[- _]?\d{3}\b",
        r"\b\d{4}-\d{4,}-\d{2}\b",
        r"\b(?:RFP|T)[- _]?\d{4}[- _]\d{3,}\b",
        r"\bIHCC[- _][A-Z]+[- _]\d+\b",
        r"\b[A-Z]\d{2}[- _]\d{3}\b",
        r"\b\d{4}-\d{2}-[A-Z0-9-]+\b",
    )
    upper = value.upper()
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, upper):
            reference = re.sub(r"[- _]+", "-", match.group(0))
            if reference not in found:
                found.append(reference)
    return tuple(found)


def load_manifest(path: Path) -> tuple[TenderFolder, ...]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    return parse_manifest(payload)


def parse_manifest(payload: Mapping[str, object]) -> tuple[TenderFolder, ...]:
    if payload.get("source") != "google_drive":
        raise ImportValidationError("Manifest source must be google_drive.")
    raw_folders = payload.get("folders")
    if not isinstance(raw_folders, list):
        raise ImportValidationError("Manifest folders must be a list.")

    folders: list[TenderFolder] = []
    seen_folder_ids: set[str] = set()
    seen_file_ids: set[str] = set()
    for raw_folder in raw_folders:
        if not isinstance(raw_folder, Mapping):
            raise ImportValidationError("Every manifest folder must be an object.")
        folder_id = _required_text(raw_folder, "drive_folder_id")
        _validate_drive_id(folder_id, "folder")
        if folder_id in seen_folder_ids:
            raise ImportValidationError(f"Duplicate Drive folder ID: {folder_id}")
        seen_folder_ids.add(folder_id)
        folder_url = _required_https_url(raw_folder, "url")
        files: list[DriveFile] = []
        raw_files = raw_folder.get("files", [])
        if not isinstance(raw_files, list):
            raise ImportValidationError(f"Files for {folder_id} must be a list.")
        for raw_file in raw_files:
            if not isinstance(raw_file, Mapping):
                raise ImportValidationError(f"Every file in {folder_id} must be an object.")
            file_id = _required_text(raw_file, "drive_file_id")
            _validate_drive_id(file_id, "file")
            if file_id in seen_file_ids:
                raise ImportValidationError(f"Duplicate Drive file ID: {file_id}")
            seen_file_ids.add(file_id)
            files.append(
                DriveFile(
                    drive_file_id=file_id,
                    name=_required_text(raw_file, "name"),
                    mime_type=_required_text(raw_file, "mime_type"),
                    url=_required_https_url(raw_file, "url"),
                    created_time=_optional_text(raw_file.get("created_time")),
                    modified_time=_optional_text(raw_file.get("modified_time")),
                    source_path=_optional_text(raw_file.get("source_path")),
                )
            )
        folders.append(
            TenderFolder(
                drive_folder_id=folder_id,
                name=_required_text(raw_folder, "name"),
                url=folder_url,
                files=tuple(files),
            )
        )
    return tuple(folders)


def plan_import(folders: Iterable[TenderFolder]) -> list[ImportDecision]:
    """Return deterministic consolidate/create-or-update/ambiguous decisions."""
    ordered = sorted((_coerce_folder(folder) for folder in folders), key=lambda item: item.drive_folder_id)
    groups: list[list[TenderFolder]] = []
    for folder in ordered:
        matching = [group for group in groups if any(_strong_match(folder, item) for item in group)]
        if not matching:
            groups.append([folder])
            continue
        primary = matching[0]
        primary.append(folder)
        for duplicate in matching[1:]:
            primary.extend(duplicate)
            groups.remove(duplicate)

    ambiguous_ids: set[str] = set()
    for group in groups:
        if len(group) != 1 or group[0].files:
            continue
        folder = group[0]
        possible = [
            other
            for other in groups
            if other is not group and any(_weak_alias(folder.name, candidate.name) for candidate in other)
        ]
        if possible:
            ambiguous_ids.add(folder.drive_folder_id)

    decisions: list[ImportDecision] = []
    for group in groups:
        group = sorted(group, key=lambda item: item.drive_folder_id)
        if len(group) == 1 and group[0].drive_folder_id in ambiguous_ids:
            folder = group[0]
            decisions.append(
                ImportDecision(
                    action="ambiguous",
                    canonical_name=folder.name.strip(),
                    source_folder_ids=(folder.drive_folder_id,),
                    reason="empty folder has a probable name alias but no reference or files to verify it",
                    folders=(folder,),
                )
            )
            continue
        canonical = max(group, key=_canonical_rank)
        files = _unique_files(group)
        action = "consolidate" if len(group) > 1 else "create_or_update"
        decisions.append(
            ImportDecision(
                action=action,
                canonical_name=canonical.name.strip(),
                source_folder_ids=tuple(item.drive_folder_id for item in group),
                reason=(
                    "matching tender/reference, normalized identity, or repeated source filenames"
                    if len(group) > 1
                    else "distinct Drive tender folder"
                ),
                reference=_canonical_reference(canonical, group),
                files=files,
                folders=tuple(group),
            )
        )
    return sorted(decisions, key=lambda item: (item.canonical_name.casefold(), item.source_folder_ids))


def import_drive_tenders(
    db: Session,
    folders: Sequence[TenderFolder],
    *,
    actor: str,
    apply: bool = False,
    imported_at: datetime | None = None,
) -> dict[str, object]:
    """Plan or apply the import in the caller's transaction.

    The caller owns commit/rollback. Applying flushes IDs for the report but never
    commits, allowing the command to keep the whole import atomic.
    """
    actor = actor.strip()
    if not actor:
        raise ImportValidationError("An audit actor is required.")
    timestamp = (imported_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    projects = list(db.scalars(select(Project)).all())
    documents = list(db.scalars(select(Document)).all())
    documents_by_drive_id = _documents_by_drive_id(documents)

    project_items: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []
    consolidated: list[dict[str, object]] = []
    summary = {"create": 0, "update": 0, "documents_create": 0, "documents_update": 0, "ambiguous": 0}

    for decision in plan_import(folders):
        if decision.action == "ambiguous":
            summary["ambiguous"] += 1
            unresolved.append(
                {
                    "name": decision.canonical_name,
                    "source_folder_ids": list(decision.source_folder_ids),
                    "reason": decision.reason,
                }
            )
            continue

        matches = _matching_projects(projects, decision)
        if len(matches) > 1:
            summary["ambiguous"] += 1
            unresolved.append(
                {
                    "name": decision.canonical_name,
                    "source_folder_ids": list(decision.source_folder_ids),
                    "reason": "multiple existing IHOS projects match this tender",
                    "project_ids": [str(project.id) for project in matches],
                }
            )
            continue

        action = "update" if matches else "create"
        summary[action] += 1
        project = matches[0] if matches else None
        if apply:
            if project is None:
                project = Project(
                    name=decision.canonical_name,
                    client_owner=_infer_client(decision),
                    tender_number=decision.reference,
                    tender_source="Google Drive",
                    status="tendering",
                    metadata_json={},
                )
                db.add(project)
                projects.append(project)
            else:
                if not project.client_owner:
                    project.client_owner = _infer_client(decision)
                if not project.tender_number:
                    project.tender_number = decision.reference
                if not project.tender_source:
                    project.tender_source = "Google Drive"
            project.metadata_json = _project_metadata(project, decision, actor, timestamp)
            db.flush()

        document_counts = {"create": 0, "update": 0}
        document_conflicts: list[dict[str, str]] = []
        for drive_file in decision.files:
            existing = documents_by_drive_id.get(drive_file.drive_file_id, [])
            if len(existing) > 1 or (existing and (project is None or existing[0].project_id != project.id)):
                document_conflicts.append(
                    {
                        "drive_file_id": drive_file.drive_file_id,
                        "name": drive_file.name,
                        "reason": "Drive file ID is already linked outside the matched project",
                    }
                )
                continue
            document_action = "update" if existing else "create"
            document_counts[document_action] += 1
            summary[f"documents_{document_action}"] += 1
            if not apply:
                continue
            if existing:
                document = existing[0]
                document.metadata_json = _document_metadata(document, drive_file, decision, actor, timestamp)
            else:
                document = Document(
                    title=drive_file.name,
                    category=_document_category(drive_file),
                    status="registered",
                    project_id=project.id,
                    storage_uri=None,
                    description="Linked Google Drive source; the original remains immutable.",
                    metadata_json=_document_metadata(None, drive_file, decision, actor, timestamp),
                )
                db.add(document)
                documents.append(document)
                documents_by_drive_id[drive_file.drive_file_id] = [document]

        if document_conflicts:
            unresolved.extend(document_conflicts)
        if apply:
            db.flush()
        project_items.append(
            {
                "action": action,
                "project_id": str(project.id) if project is not None else None,
                "name": project.name if project is not None else decision.canonical_name,
                "tender_reference": decision.reference,
                "source_folder_ids": list(decision.source_folder_ids),
                "file_count": len(decision.files),
                "document_actions": document_counts,
            }
        )
        if decision.action == "consolidate":
            consolidated.append(
                {
                    "project_name": decision.canonical_name,
                    "source_folder_ids": list(decision.source_folder_ids),
                    "reason": decision.reason,
                }
            )

    return {
        "status": "applied" if apply else "dry_run",
        "source": "google_drive",
        "actor": actor,
        "imported_at": timestamp,
        "summary": summary,
        "projects": project_items,
        "consolidated_folders": consolidated,
        "unresolved": unresolved,
    }


def _coerce_folder(folder: TenderFolder) -> TenderFolder:
    files: list[DriveFile] = []
    for raw in folder.files:
        if isinstance(raw, DriveFile):
            files.append(raw)
        else:
            file_id = raw.get("drive_file_id") or raw.get("id")
            name = raw.get("name") or raw.get("title")
            if not file_id or not name:
                continue
            files.append(
                DriveFile(
                    drive_file_id=str(file_id),
                    name=str(name),
                    mime_type=str(raw.get("mime_type") or "application/octet-stream"),
                    url=str(raw.get("url") or ""),
                    created_time=_optional_text(raw.get("created_time")),
                    modified_time=_optional_text(raw.get("modified_time")),
                    source_path=_optional_text(raw.get("source_path")),
                )
            )
    return TenderFolder(folder.drive_folder_id, folder.name, folder.url, tuple(files))


def _strong_match(left: TenderFolder, right: TenderFolder) -> bool:
    left_references = _folder_references(left)
    right_references = _folder_references(right)
    if left_references & right_references:
        return True
    if _names_overlap(normalize_tender_name(left.name), normalize_tender_name(right.name)):
        return True
    left_names = {_file_signature(item.name) for item in left.files}
    right_names = {_file_signature(item.name) for item in right.files}
    return len((left_names & right_names) - {""}) >= 2


def _weak_alias(left: str, right: str) -> bool:
    left_tokens = [token for token in normalize_tender_name(left).split() if len(token) >= 4]
    right_tokens = [token for token in normalize_tender_name(right).split() if len(token) >= 4]
    return any(SequenceMatcher(None, a, b).ratio() >= 0.78 for a in left_tokens for b in right_tokens)


def _names_overlap(left: str, right: str) -> bool:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    significant = {"sewer", "separation", "sanitary", "manhole", "fernie", "cumberland", "firehall", "storm"}
    common = left_tokens & right_tokens
    return len(common) >= 3 or len(common & significant) >= 2


def _folder_references(folder: TenderFolder) -> set[str]:
    references = set(extract_references(folder.name))
    for drive_file in folder.files:
        references.update(extract_references(drive_file.name))
    return references


def _canonical_reference(canonical: TenderFolder, group: Sequence[TenderFolder]) -> str | None:
    reference = extract_reference(canonical.name)
    if reference:
        return reference
    for folder in group:
        reference = extract_reference(folder.name)
        if reference:
            return reference
    for drive_file in _unique_files(group):
        reference = extract_reference(drive_file.name)
        if reference:
            return reference
    return None


def _canonical_rank(folder: TenderFolder) -> tuple[int, int, int, str]:
    return (bool(extract_reference(folder.name)), len(folder.name.strip()), len(folder.files), folder.name)


def _unique_files(group: Sequence[TenderFolder]) -> tuple[DriveFile, ...]:
    by_id: dict[str, DriveFile] = {}
    for folder in group:
        for drive_file in folder.files:
            if isinstance(drive_file, DriveFile):
                by_id.setdefault(drive_file.drive_file_id, drive_file)
    return tuple(sorted(by_id.values(), key=lambda item: (item.name.casefold(), item.drive_file_id)))


def _file_signature(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _matching_projects(projects: Sequence[Project], decision: ImportDecision) -> list[Project]:
    folder_ids = set(decision.source_folder_ids)
    matches: list[Project] = []
    for project in projects:
        metadata = project.metadata_json or {}
        source = metadata.get(SOURCE_KEY, {}) if isinstance(metadata, Mapping) else {}
        existing_ids = set(source.get("source_folder_ids", [])) if isinstance(source, Mapping) else set()
        reference_match = bool(
            decision.reference and project.tender_number and decision.reference == project.tender_number.upper()
        )
        name_match = normalize_tender_name(project.name) == normalize_tender_name(decision.canonical_name)
        if folder_ids & existing_ids or reference_match or name_match:
            matches.append(project)
    return matches


def _documents_by_drive_id(documents: Sequence[Document]) -> dict[str, list[Document]]:
    indexed: dict[str, list[Document]] = {}
    for document in documents:
        metadata = document.metadata_json or {}
        drive_file_id = metadata.get("drive_file_id") if isinstance(metadata, Mapping) else None
        if isinstance(drive_file_id, str):
            indexed.setdefault(drive_file_id, []).append(document)
    return indexed


def _project_metadata(
    project: Project,
    decision: ImportDecision,
    actor: str,
    timestamp: str,
) -> dict[str, object]:
    metadata = dict(project.metadata_json or {})
    metadata[SOURCE_KEY] = {
        "source_folder_ids": list(decision.source_folder_ids),
        "source_folder_urls": [folder.url for folder in decision.folders],
        "imported_at": timestamp,
        "audit_actor": actor,
        "source_immutable": True,
    }
    return metadata


def _document_metadata(
    document: Document | None,
    drive_file: DriveFile,
    decision: ImportDecision,
    actor: str,
    timestamp: str,
) -> dict[str, object]:
    metadata = dict(document.metadata_json or {}) if document is not None else {}
    metadata.update(
        {
            "external_provider": "google_drive",
            "drive_file_id": drive_file.drive_file_id,
            "drive_url": drive_file.url,
            "mime_type": drive_file.mime_type,
            "original_filename": drive_file.name,
            "drive_created_time": drive_file.created_time,
            "drive_modified_time": drive_file.modified_time,
            "source_path": drive_file.source_path,
            "source_folder_ids": list(decision.source_folder_ids),
            "imported_at": timestamp,
            "audit_actor": actor,
            "source_immutable": True,
        }
    )
    return metadata


def _document_category(drive_file: DriveFile) -> str:
    name = drive_file.name.casefold()
    if "drawing" in name or "_ift" in name or "-ift" in name:
        return "drawing"
    if "geotech" in name:
        return "geotechnical"
    if "addend" in name:
        return "addendum"
    if "spec" in name:
        return "specification"
    return "other"


def _infer_client(decision: ImportDecision) -> str | None:
    haystack = " ".join([decision.canonical_name, *(item.name for item in decision.files)]).casefold()
    clients = (
        ("fernie", "City of Fernie"),
        ("cumberland", "Village of Cumberland"),
        ("port edward", "District of Port Edward"),
        ("parksville", "City of Parksville"),
        ("mcleod lake", "McLeod Lake Indian Band"),
    )
    return next((client for marker, client in clients if marker in haystack), None)


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ImportValidationError(f"Manifest field {key} must be non-empty text.")
    return value.strip()


def _required_https_url(payload: Mapping[str, object], key: str) -> str:
    value = _required_text(payload, key)
    if not value.startswith("https://"):
        raise ImportValidationError(f"Manifest field {key} must be an HTTPS URL.")
    return value


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _validate_drive_id(value: str, kind: str) -> None:
    if not _DRIVE_ID.fullmatch(value):
        raise ImportValidationError(f"Invalid Drive {kind} ID: {value}")
