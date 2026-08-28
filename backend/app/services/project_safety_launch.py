from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError

from app.core.errors import AppError
from app.models.project import Project
from app.schemas.project_folder import ProjectFolderEntry
from app.schemas.project_safety_launch import ProjectSafetyLaunchRead


SAFETY_FOLDER_RELATIVE_PATH = "13_Award_Handoff/Safety"
SAFETY_FOLDER_DESCRIPTION = (
    "Internal project safety launch records; prepared path only and not safety evidence."
)
SAFETY_RECORD_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("project_safety_plan", "Project-specific safety plan"),
    ("emergency_action_card", "Emergency action card"),
    ("field_hazard_assessment", "Field-level hazard assessment"),
    ("toolbox_talk", "Crew toolbox talk"),
    ("safety_permit", "Task permit or safety-control record, if applicable"),
    ("orientation_verification", "Crew orientation and qualification verification"),
)


def initialize(project: Project, *, actor: str) -> ProjectSafetyLaunchRead:
    if project.status != "awarded" or not str(project.project_number or "").strip():
        raise AppError(
            "Safety launch initialization requires an awarded project with a permanent job number.",
            status_code=409,
        )
    if not project.workspace_root or not project.workspace_manifest_json:
        raise AppError(
            "The awarded project workspace must exist before safety launch initialization.",
            status_code=409,
        )

    folder_path = f"{project.workspace_root}/{SAFETY_FOLDER_RELATIVE_PATH}"
    metadata = dict(project.metadata_json or {})
    existing = metadata.get("safety_launch")
    if existing is not None:
        launch = _read(existing)
        if (
            launch.project_id != project.id
            or launch.job_number != project.project_number
            or launch.folder_path != folder_path
        ):
            raise AppError(
                "The existing safety launch shell belongs to a different project, job number, or folder.",
                status_code=409,
            )
        _ensure_folder_entry(project, folder_path)
        return launch

    launch = ProjectSafetyLaunchRead(
        project_id=project.id,
        job_number=str(project.project_number),
        release_status="blocked",
        folder_path=folder_path,
        folder_status="prepared",
        record_requirements=[
            {
                "code": code,
                "label": label,
                "applicability_status": "unconfirmed",
                "status": "not_started",
                "record_id": None,
                "evidence_document_ids": [],
            }
            for code, label in SAFETY_RECORD_REQUIREMENTS
        ],
        portal_access={
            "status": "not_started",
            "automatic_provisioning": False,
            "assignments": [],
        },
        initialized_by=actor,
        initialized_at=datetime.now(UTC),
    )
    _ensure_folder_entry(project, folder_path)
    metadata["safety_launch"] = launch.model_dump(mode="json")
    project.metadata_json = metadata
    return launch


def read(project: Project) -> ProjectSafetyLaunchRead | None:
    value = (project.metadata_json or {}).get("safety_launch")
    if value is None:
        return None
    launch = _read(value)
    _require_matching_identity(project, launch)
    return launch


def portal_access_allowed(project: Project, employee_id: UUID) -> bool:
    value = (project.metadata_json or {}).get("safety_launch")
    if value is None:
        return True
    try:
        launch = ProjectSafetyLaunchRead.model_validate(value)
    except ValidationError:
        return False
    if not _matching_identity(project, launch):
        return False
    return launch.portal_access.status == "active" and any(
        assignment.employee_id == employee_id and assignment.status == "active"
        for assignment in launch.portal_access.assignments
    )


def require_portal_access(project: Project, employee_id: UUID) -> None:
    if not portal_access_allowed(project, employee_id):
        raise AppError(
            "Project portal access has not been assigned for this controlled job.",
            status_code=403,
        )


def _read(value: object) -> ProjectSafetyLaunchRead:
    try:
        return ProjectSafetyLaunchRead.model_validate(value)
    except ValidationError as error:
        raise AppError(
            "The existing safety launch shell is invalid and requires management review.",
            status_code=409,
        ) from error


def _matching_identity(project: Project, launch: ProjectSafetyLaunchRead) -> bool:
    expected_folder = (
        f"{project.workspace_root}/{SAFETY_FOLDER_RELATIVE_PATH}"
        if project.workspace_root
        else None
    )
    return (
        launch.project_id == project.id
        and launch.job_number == project.project_number
        and launch.folder_path == expected_folder
    )


def _require_matching_identity(project: Project, launch: ProjectSafetyLaunchRead) -> None:
    if not _matching_identity(project, launch):
        raise AppError(
            "The safety launch shell belongs to a different project, job number, or folder.",
            status_code=409,
        )


def _ensure_folder_entry(project: Project, folder_path: str) -> None:
    manifest = dict(project.workspace_manifest_json or {})
    entries = list(manifest.get("entries") or [])
    matching = [entry for entry in entries if entry.get("path") == folder_path]
    if len(matching) > 1:
        raise AppError(
            "The awarded workspace contains duplicate safety folder entries.",
            status_code=409,
        )
    if matching:
        entry = ProjectFolderEntry.model_validate(matching[0])
        if entry.kind != "folder":
            raise AppError(
                "The awarded workspace safety path is not a folder.",
                status_code=409,
            )
        return
    entries.append(
        ProjectFolderEntry(
            path=folder_path,
            kind="folder",
            description=SAFETY_FOLDER_DESCRIPTION,
        ).model_dump(mode="json")
    )
    manifest["entries"] = entries
    project.workspace_manifest_json = manifest
