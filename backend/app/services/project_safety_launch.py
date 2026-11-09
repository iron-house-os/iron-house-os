from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.document import Document
from app.models.field_operations import FieldRecord
from app.models.project import Project
from app.models.user import Employee, UserAccount
from app.schemas.project_folder import ProjectFolderEntry
from app.schemas.project_safety_launch import (
    ProjectSafetyLaunchRead,
    ProjectSafetyLaunchUpdate,
    ProjectSafetyRecordRequirement,
    ProjectSafetyReviewEvent,
)


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
SUPPORTED_RECORD_TYPES: dict[str, tuple[str, set[str]] | None] = {
    "project_safety_plan": None,
    "emergency_action_card": ("emergency_action_card", {"ready"}),
    "field_hazard_assessment": ("daily_hazard_assessment", {"released"}),
    "toolbox_talk": ("toolbox_talk", {"submitted", "ready", "completed", "closed"}),
    "safety_permit": ("safety_permit", {"ready"}),
    "orientation_verification": None,
}
VALID_EVIDENCE_DOCUMENT_STATUSES = {"registered", "active", "current"}


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


def update(
    db: Session,
    project: Project,
    payload: ProjectSafetyLaunchUpdate,
    *,
    actor: str,
) -> ProjectSafetyLaunchRead:
    launch = read(project)
    if launch is None:
        raise AppError("Project safety launch controls are not initialized.", status_code=404)
    if project.status not in {"awarded", "construction"}:
        raise AppError(
            "Safety launch controls can only be updated for awarded or construction projects.",
            status_code=409,
        )

    expected_codes = [code for code, _label in SAFETY_RECORD_REQUIREMENTS]
    submitted_codes = [item.code for item in payload.record_requirements]
    if len(submitted_codes) != len(set(submitted_codes)):
        raise AppError("Safety launch requirements cannot contain duplicate control codes.", status_code=409)
    if set(submitted_codes) != set(expected_codes) or len(submitted_codes) != len(expected_codes):
        raise AppError("Every safety launch requirement must be supplied exactly once.", status_code=409)

    assignment_ids = [item.employee_id for item in payload.portal_access.assignments]
    if len(assignment_ids) != len(set(assignment_ids)):
        raise AppError("Project portal assignments cannot contain duplicate employees.", status_code=409)
    employees = {
        item.id: item
        for item in db.scalars(select(Employee).where(Employee.id.in_(assignment_ids))).all()
    } if assignment_ids else {}
    for assignment in payload.portal_access.assignments:
        employee = employees.get(assignment.employee_id)
        if employee is None or employee.status != "active":
            raise AppError("Project portal assignments require active employee records.", status_code=409)
        account = db.scalar(
            select(UserAccount).where(func.lower(UserAccount.email) == employee.email.lower())
        )
        if account is None or not account.is_active:
            raise AppError(
                "Project portal assignments require an active portal account created through onboarding or employee activation.",
                status_code=409,
            )
        if employee.portal_role not in {"employee", "operator", "foreman"}:
            raise AppError("Management profiles cannot be assigned as project crew portal users.", status_code=409)
        if assignment.portal_role != employee.portal_role:
            raise AppError("A project portal assignment must use the employee's approved portal role.", status_code=409)
    if payload.portal_access.status == "active" and not any(
        item.status == "active" for item in payload.portal_access.assignments
    ):
        raise AppError("Active project portal access requires at least one active employee assignment.", status_code=409)
    if payload.portal_access.status == "not_started" and any(
        item.status == "active" for item in payload.portal_access.assignments
    ):
        raise AppError("Portal access cannot remain not started while employee assignments are active.", status_code=409)

    labels = {code: label for code, label in SAFETY_RECORD_REQUIREMENTS}
    now = datetime.now(UTC)
    requirements: list[ProjectSafetyRecordRequirement] = []
    for code in expected_codes:
        item = next(candidate for candidate in payload.record_requirements if candidate.code == code)
        basis = (item.not_applicable_basis or "").strip() or None
        if len(item.evidence_document_ids) != len(set(item.evidence_document_ids)):
            raise AppError(f"{labels[code]} contains duplicate evidence documents.", status_code=409)
        if item.applicability_status == "unconfirmed":
            if item.status != "not_started" or item.record_id or item.evidence_document_ids or basis:
                raise AppError(
                    f"{labels[code]} must remain empty and not started until applicability is confirmed.",
                    status_code=409,
                )
        elif item.applicability_status == "not_applicable":
            if item.status != "ready" or not basis or len(basis) < 10:
                raise AppError(
                    f"{labels[code]} requires a written not-applicable basis of at least 10 characters.",
                    status_code=409,
                )
            if item.record_id or item.evidence_document_ids:
                raise AppError(
                    f"{labels[code]} cannot retain evidence links when marked not applicable.",
                    status_code=409,
                )
        else:
            if basis:
                raise AppError(
                    f"{labels[code]} cannot include a not-applicable basis when it is applicable.",
                    status_code=409,
                )
            _require_valid_documents(db, project, item.evidence_document_ids, labels[code])
            if item.record_id:
                _require_valid_record(db, project, code, item.record_id, labels[code])
            if item.status == "ready" and not item.evidence_document_ids:
                raise AppError(
                    f"{labels[code]} requires at least one current project document before it can be ready.",
                    status_code=409,
                )
        requirements.append(
            ProjectSafetyRecordRequirement(
                code=code,
                label=labels[code],
                applicability_status=item.applicability_status,
                status=item.status,
                record_id=item.record_id,
                evidence_document_ids=item.evidence_document_ids,
                not_applicable_basis=basis,
                reviewed_by=actor,
                reviewed_at=now,
            )
        )

    candidate = launch.model_copy(
        update={
            "release_status": payload.release_status,
            "record_requirements": requirements,
            "portal_access": launch.portal_access.model_copy(
                update={
                    "status": payload.portal_access.status,
                    "assignments": payload.portal_access.assignments,
                    "automatic_provisioning": False,
                }
            ),
            "last_reviewed_by": actor,
            "last_reviewed_at": now,
            "last_review_note": payload.review_note.strip(),
        }
    )
    if payload.release_status == "ready":
        if not payload.release_confirmation:
            raise AppError("An explicit human confirmation is required for a Ready safety release.", status_code=409)
        unresolved = unresolved_requirements(db, project, candidate)
        if unresolved:
            raise AppError(
                "Safety release cannot be Ready until every requirement has valid project evidence or a documented not-applicable basis.",
                status_code=409,
            )

    history = [
        *launch.review_history,
        ProjectSafetyReviewEvent(
            reviewed_by=actor,
            reviewed_at=now,
            review_note=payload.review_note.strip(),
            release_status=payload.release_status,
            portal_status=payload.portal_access.status,
            active_assignment_count=sum(
                1 for item in payload.portal_access.assignments if item.status == "active"
            ),
        ),
    ][-100:]
    candidate = candidate.model_copy(update={"review_history": history})
    metadata = dict(project.metadata_json or {})
    metadata["safety_launch"] = candidate.model_dump(mode="json")
    project.metadata_json = metadata
    return candidate


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


def unresolved_requirements(
    db: Session,
    project: Project,
    launch: ProjectSafetyLaunchRead,
) -> list[ProjectSafetyRecordRequirement]:
    return [item for item in launch.record_requirements if not requirement_resolved(db, project, item)]


def requirement_resolved(
    db: Session,
    project: Project,
    item: ProjectSafetyRecordRequirement,
) -> bool:
    if item.applicability_status == "unconfirmed":
        return False
    if item.applicability_status == "not_applicable":
        return item.status == "ready" and len((item.not_applicable_basis or "").strip()) >= 10
    if item.status != "ready" or not item.evidence_document_ids:
        return False
    if not _documents_are_valid(db, project, item.evidence_document_ids):
        return False
    if item.record_id and not _record_is_valid(db, project, item.code, item.record_id):
        return False
    return True


def _require_valid_documents(
    db: Session,
    project: Project,
    document_ids: list[UUID],
    label: str,
) -> None:
    if not _documents_are_valid(db, project, document_ids):
        raise AppError(
            f"{label} evidence must use current, stored documents linked to this exact project.",
            status_code=409,
        )


def _documents_are_valid(db: Session, project: Project, document_ids: list[UUID]) -> bool:
    if not document_ids:
        return True
    documents = list(db.scalars(select(Document).where(Document.id.in_(document_ids))).all())
    return len(documents) == len(set(document_ids)) and all(
        item.project_id == project.id
        and item.status in VALID_EVIDENCE_DOCUMENT_STATUSES
        and bool((item.storage_uri or "").strip())
        for item in documents
    )


def _require_valid_record(
    db: Session,
    project: Project,
    requirement_code: str,
    record_id: UUID,
    label: str,
) -> None:
    if not _record_is_valid(db, project, requirement_code, record_id):
        raise AppError(
            f"{label} references an unsupported, incomplete, or wrong-project operational record.",
            status_code=409,
        )


def _record_is_valid(
    db: Session,
    project: Project,
    requirement_code: str,
    record_id: UUID,
) -> bool:
    supported = SUPPORTED_RECORD_TYPES.get(requirement_code)
    if supported is None:
        return False
    expected_type, accepted_statuses = supported
    record = db.get(FieldRecord, record_id)
    return bool(
        record
        and record.project_id == project.id
        and record.record_type == expected_type
        and record.status in accepted_statuses
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
