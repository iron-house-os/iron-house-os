from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.field_operations import FieldRecord
from app.models.project import Project, ProjectStartChecklistItem
from app.models.user import Employee
from app.schemas.project_folder import ProjectFolderEntry
from app.services import project_safety_launch


PRODUCTION_FOLDER_RELATIVE_PATH = "13_Award_Handoff/Field_Production"
PRODUCTION_FOLDER_STRUCTURE: tuple[tuple[str, str], ...] = (
    (PRODUCTION_FOLDER_RELATIVE_PATH, "Internal approved field-production records."),
    (
        f"{PRODUCTION_FOLDER_RELATIVE_PATH}/Daily_Reports",
        "Generated approved daily report references.",
    ),
    (
        f"{PRODUCTION_FOLDER_RELATIVE_PATH}/Photos",
        "Project-linked field photo evidence references.",
    ),
    (
        f"{PRODUCTION_FOLDER_RELATIVE_PATH}/Tickets",
        "Project-linked delivery, disposal and field ticket evidence references.",
    ),
)


def posting_blockers(db: Session, project: Project) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if project.status not in {"awarded", "construction"}:
        blockers.append(
            {
                "code": "project_status",
                "message": "The project must be awarded or in construction before field production can post.",
            }
        )
    if not str(project.project_number or "").strip():
        blockers.append(
            {
                "code": "job_number",
                "message": "A permanent job number is required before field production can post.",
            }
        )
    if not project.workspace_root or not project.workspace_manifest_json:
        blockers.append(
            {
                "code": "workspace",
                "message": "The awarded project workspace must exist before field production can post.",
            }
        )

    launch = project_safety_launch.read(project)
    if launch is None:
        blockers.append(
            {
                "code": "safety_launch",
                "message": "The controlled safety launch must be initialized before field production can post.",
            }
        )
    else:
        if launch.release_status != "ready":
            blockers.append(
                {
                    "code": "safety_release",
                    "message": "Safety release must be Ready before field production can post.",
                }
            )
        unresolved = []
        for item in launch.record_requirements:
            if item.applicability_status == "unconfirmed":
                unresolved.append(item)
                continue
            if item.applicability_status != "applicable":
                continue
            record = db.get(FieldRecord, item.record_id) if item.record_id else None
            if (
                item.status != "ready"
                or record is None
                or record.project_id != project.id
                or record.record_type != item.code
                or record.status != "ready"
            ):
                unresolved.append(item)
        if unresolved:
            blockers.append(
                {
                    "code": "safety_records",
                    "message": "Applicable safety records and their evidence must be resolved before field production can post.",
                }
            )
        active_assignments = []
        for item in launch.portal_access.assignments:
            employee = db.get(Employee, item.employee_id)
            if item.status == "active" and employee is not None and employee.status == "active":
                active_assignments.append(item)
        if launch.portal_access.status != "active" or not active_assignments:
            blockers.append(
                {
                    "code": "portal_access",
                    "message": "Project portal access and at least one worker assignment must be active before field production can post.",
                }
            )

    checklist = list(
        db.scalars(select(ProjectStartChecklistItem).where(ProjectStartChecklistItem.project_id == project.id)).all()
    )
    if not checklist or any(not item.completed for item in checklist):
        blockers.append(
            {
                "code": "mobilization",
                "message": "The project-start checklist must be complete before field production can post.",
            }
        )
    return blockers


def require_posting_ready(db: Session, project: Project) -> None:
    blockers = posting_blockers(db, project)
    if blockers:
        raise AppError(
            "Field production posting is blocked: " + "; ".join(item["message"] for item in blockers),
            status_code=409,
        )


def ensure_workspace_folders(project: Project) -> dict[str, str]:
    if not project.workspace_root or not project.workspace_manifest_json:
        raise AppError(
            "The awarded project workspace must exist before field production can post.",
            status_code=409,
        )
    manifest = dict(project.workspace_manifest_json)
    entries = list(manifest.get("entries") or [])
    paths: dict[str, str] = {}
    for relative_path, description in PRODUCTION_FOLDER_STRUCTURE:
        full_path = f"{project.workspace_root}/{relative_path}"
        paths[relative_path] = full_path
        matching = [entry for entry in entries if entry.get("path") == full_path]
        if len(matching) > 1:
            raise AppError(
                "The awarded workspace contains duplicate field-production folder entries.",
                status_code=409,
            )
        if matching:
            entry = ProjectFolderEntry.model_validate(matching[0])
            if entry.kind != "folder":
                raise AppError(
                    "An awarded workspace field-production path is not a folder.",
                    status_code=409,
                )
            continue
        entries.append(
            ProjectFolderEntry(
                path=full_path,
                kind="folder",
                description=description,
            ).model_dump(mode="json")
        )
    manifest["entries"] = entries
    project.workspace_manifest_json = manifest
    return paths


def workspace_folder_status(project: Project) -> str:
    if not project.workspace_root or not project.workspace_manifest_json:
        return "not_initialized"
    expected = f"{project.workspace_root}/{PRODUCTION_FOLDER_RELATIVE_PATH}"
    matches = [
        entry
        for entry in (project.workspace_manifest_json.get("entries") or [])
        if entry.get("path") == expected and entry.get("kind") == "folder"
    ]
    return "prepared" if len(matches) == 1 else "not_initialized"
