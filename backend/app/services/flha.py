from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.field_operations import FieldRecord
from app.models.project import Project
from app.models.user import Employee
from app.models.media import MediaRecordLink
from app.schemas.field_operations import (
    FLHACreate,
    FLHADetails,
    FLHAReassessment,
    FLHARelease,
    FLHASignatureCreate,
    FLHASuggestion,
    FLHASuggestionRequest,
    FLHAUpdate,
    FieldRecordRead,
)
from app.services.auth import AuthenticatedUser


SCREENING_KEYS = {
    "first_aid_equipment",
    "overhead_hazards",
    "underground_utilities_locates",
    "mobile_equipment",
    "confined_space",
    "excavation_sloping_shoring_access",
    "additional_ppe",
    "traffic_control",
    "subcontractors",
    "basic_ppe_review",
}
SUPERVISOR_ROLES = {"admin", "operations_manager"}
PRESETS = [
    {
        "name": "Excavation and utilities",
        "tasks": [
            {
                "task": "Excavate and install utilities",
                "hazard": "Cave-in, utility strike, unsafe access or mobile equipment interaction",
                "control": "Verify current locates, protective system, ladder access and exclusion zone in the field.",
                "control_hierarchy": "engineering",
                "critical": True,
                "evidence_required": True,
            }
        ],
    },
    {
        "name": "Traffic interface",
        "tasks": [
            {
                "task": "Work beside public traffic",
                "hazard": "Worker or equipment struck by moving traffic",
                "control": "Implement the approved traffic-control plan with trained persons and verified devices.",
                "control_hierarchy": "administrative",
                "critical": True,
                "evidence_required": True,
            }
        ],
    },
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _profile(db: Session, user: AuthenticatedUser) -> Employee | None:
    return db.scalar(select(Employee).where(Employee.email.ilike(user.email)))


def _portal_role(profile: Employee | None) -> str | None:
    return profile.portal_role if profile else None


def _is_supervisor(user: AuthenticatedUser, profile: Employee | None) -> bool:
    return user.role in SUPERVISOR_ROLES or _portal_role(profile) in {"foreman", "management"}


def _audit(user: AuthenticatedUser, action: str, **metadata: object) -> dict:
    return {
        "action": action,
        "actor_email": user.email,
        "actor_name": user.display_name,
        "timestamp": _now(),
        "metadata": metadata,
    }


def _details_payload(
    details: FLHADetails,
    *,
    user: AuthenticatedUser,
    version: int,
    source_record_id: UUID | None = None,
    root_record_id: UUID | None = None,
    reason: str | None = None,
    action: str = "created",
) -> dict:
    values = details.model_dump(mode="json")
    values.update(
        {
            "flha_version": version,
            "source_record_id": str(source_record_id) if source_record_id else None,
            "root_record_id": str(root_record_id) if root_record_id else None,
            "reassessment_reason": reason,
            "audit_trail": [_audit(user, action, version=version, reason=reason)],
            "ai_advisory_only": True,
        }
    )
    return values


def _blockers(details: FLHADetails | dict, linked_evidence_ids: set[str] | None = None) -> list[str]:
    parsed = details if isinstance(details, FLHADetails) else FLHADetails.model_validate(details)
    blockers: list[str] = []
    screening = {item.key for item in parsed.screening}
    missing_screening = sorted(SCREENING_KEYS - screening)
    if missing_screening:
        blockers.append("Complete every required Yes / No / N/A screening item.")
    for index, row in enumerate(parsed.tasks, start=1):
        if not row.critical:
            continue
        if not row.control_accepted:
            blockers.append(f"Critical hazard row {index} requires an accepted control.")
        if not row.control.strip():
            blockers.append(f"Critical hazard row {index} requires a control.")
        if not row.responsible_person.strip():
            blockers.append(f"Critical hazard row {index} requires a responsible person.")
        if row.evidence_required and not ({str(item) for item in row.evidence_ids} & (linked_evidence_ids or set())):
            blockers.append(f"Critical hazard row {index} requires evidence.")
    return blockers



def _linked_evidence_ids(db: Session, item: FieldRecord) -> set[str]:
    return {
        str(asset_id)
        for asset_id in db.scalars(
            select(MediaRecordLink.asset_id).where(
                MediaRecordLink.record_type == "field_record", MediaRecordLink.record_id == item.id
            )
        )
    }


def _validate_crew(db: Session, details: FLHADetails) -> None:
    for member in details.crew:
        employee = db.get(Employee, member.employee_id)
        if employee is None or employee.status != "active":
            raise AppError(f"Crew member {member.employee_name} is not an active employee.", status_code=422)


def _authorize_create(db: Session, details: FLHADetails, user: AuthenticatedUser) -> Employee | None:
    profile = _profile(db, user)
    if user.role != "viewer":
        return profile
    if profile is None:
        raise AppError("Your employee profile is not linked to this account.", status_code=400)
    crew_ids = {member.employee_id for member in details.crew}
    if _portal_role(profile) not in {"foreman", "management"} and crew_ids != {profile.id}:
        raise AppError("Employees and operators can only create an FLHA for themselves.", status_code=403)
    return profile


def _require_flha(db: Session, record_id: UUID) -> FieldRecord:
    item = db.get(FieldRecord, record_id)
    if item is None or item.record_type != "daily_hazard_assessment":
        raise AppError("FLHA not found.", status_code=404)
    return item


def _crew_ids(item: FieldRecord) -> set[str]:
    return {str(member.get("employee_id")) for member in (item.details or {}).get("crew", [])}


def _authorize_read(db: Session, item: FieldRecord, user: AuthenticatedUser) -> Employee | None:
    profile = _profile(db, user)
    if user.role in SUPERVISOR_ROLES or item.submitted_by.lower() == user.email.lower():
        return profile
    if profile and (str(profile.id) in _crew_ids(item) or _is_supervisor(user, profile)):
        return profile
    raise AppError("FLHA not found.", status_code=404)


def _authorize_edit(db: Session, item: FieldRecord, user: AuthenticatedUser) -> Employee | None:
    profile = _authorize_read(db, item, user)
    if item.submitted_by.lower() == user.email.lower() or _is_supervisor(user, profile):
        return profile
    raise AppError("You do not have permission to edit this FLHA.", status_code=403)


def _schema(item: FieldRecord) -> FieldRecordRead:
    return FieldRecordRead.model_validate(item)


def create_flha(db: Session, payload: FLHACreate, user: AuthenticatedUser) -> FieldRecordRead:
    if db.get(Project, payload.project_id) is None:
        raise AppError("Project not found.", status_code=404)
    _validate_crew(db, payload.details)
    profile = _authorize_create(db, payload.details, user)
    blockers = _blockers(payload.details)
    details = _details_payload(payload.details, user=user, version=1)
    details["release_blockers"] = blockers
    item = FieldRecord(
        record_type="daily_hazard_assessment",
        project_id=payload.project_id,
        employee_id=profile.id if profile else None,
        work_date=payload.work_date,
        title=payload.title,
        status="blocked" if blockers else "draft",
        severity="critical" if blockers else "none",
        details=details,
        document_ids=[],
        signatures=[],
        alert_recipients=[],
        submitted_by=user.email,
    )
    db.add(item)
    db.flush()
    details["root_record_id"] = str(item.id)
    item.details = details
    db.commit()
    db.refresh(item)
    return _schema(item)


def get_flha(db: Session, record_id: UUID, user: AuthenticatedUser) -> FieldRecordRead:
    item = _require_flha(db, record_id)
    _authorize_read(db, item, user)
    return _schema(item)


def update_flha(
    db: Session, record_id: UUID, payload: FLHAUpdate, user: AuthenticatedUser
) -> FieldRecordRead:
    item = _require_flha(db, record_id)
    _authorize_edit(db, item, user)
    if item.signatures or item.status in {"released", "signed"}:
        raise AppError("Released or signed FLHAs are immutable; create a reassessment.", status_code=409)
    _validate_crew(db, payload.details)
    previous = item.details or {}
    blockers = _blockers(payload.details, _linked_evidence_ids(db, item))
    updated = payload.details.model_dump(mode="json")
    for key in ("flha_version", "source_record_id", "root_record_id", "reassessment_reason", "ai_advisory_only"):
        updated[key] = previous.get(key)
    updated["release_blockers"] = blockers
    updated["audit_trail"] = [
        *(previous.get("audit_trail") or []),
        _audit(user, "edited", change_summary=payload.change_summary),
    ]
    item.details = updated
    item.title = payload.title or item.title
    item.status = "blocked" if blockers else "draft"
    item.severity = "critical" if blockers else "none"
    db.commit()
    db.refresh(item)
    return _schema(item)


def release_flha(
    db: Session, record_id: UUID, payload: FLHARelease, user: AuthenticatedUser
) -> FieldRecordRead:
    item = _require_flha(db, record_id)
    profile = _authorize_edit(db, item, user)
    if not _is_supervisor(user, profile):
        raise AppError("Supervisor or foreperson access is required to release an FLHA.", status_code=403)
    if item.signatures or item.status in {"released", "signed"}:
        raise AppError("This FLHA version has already been released.", status_code=409)
    if not payload.field_conditions_verified:
        raise AppError("The responsible field person must verify actual site conditions.", status_code=422)
    blockers = _blockers(item.details or {}, _linked_evidence_ids(db, item))
    if blockers:
        raise AppError("FLHA remains blocked: " + " ".join(blockers), status_code=409)
    details = dict(item.details or {})
    details["released_by"] = user.email
    details["released_at"] = _now()
    details["field_conditions_verified"] = True
    details["release_note"] = payload.release_note
    details["release_blockers"] = []
    details["audit_trail"] = [
        *(details.get("audit_trail") or []),
        _audit(user, "supervisor_released", release_note=payload.release_note),
    ]
    item.details = details
    item.status = "released"
    item.severity = "none"
    db.commit()
    db.refresh(item)
    return _schema(item)


def sign_flha(
    db: Session, record_id: UUID, payload: FLHASignatureCreate, user: AuthenticatedUser
) -> FieldRecordRead:
    item = _require_flha(db, record_id)
    profile = _authorize_read(db, item, user)
    if item.status not in {"released", "signed"}:
        raise AppError("A supervisor must release the FLHA before crew acknowledgement.", status_code=409)
    employee = db.get(Employee, payload.employee_id)
    if employee is None or str(employee.id) not in _crew_ids(item):
        raise AppError("Only listed crew members may sign this FLHA.", status_code=403)
    supervised = payload.supervised_shared_device
    if employee.email.lower() != user.email.lower():
        if not supervised or not _is_supervisor(user, profile):
            raise AppError("Use the worker's own device or a supervised foreperson flow.", status_code=403)
    if any(entry.get("employee_id") == str(employee.id) for entry in (item.signatures or [])):
        raise AppError("That crew member has already signed this version.", status_code=409)
    signatures = [
        *(item.signatures or []),
        {
            "employee_id": str(employee.id),
            "employee_name": payload.employee_name,
            "acknowledgement": payload.acknowledgement,
            "signed_at": _now(),
            "signed_by_account": user.email,
            "supervised_shared_device": supervised,
            "flha_version": str((item.details or {}).get("flha_version", 1)),
        },
    ]
    item.signatures = signatures
    item.status = "signed" if _crew_ids(item) <= {entry["employee_id"] for entry in signatures} else "released"
    details = dict(item.details or {})
    details["audit_trail"] = [
        *(details.get("audit_trail") or []),
        _audit(
            user,
            "crew_signed",
            employee_id=str(employee.id),
            employee_name=payload.employee_name,
            supervised_shared_device=supervised,
        ),
    ]
    item.details = details
    db.commit()
    db.refresh(item)
    return _schema(item)


def reassess_flha(
    db: Session, record_id: UUID, payload: FLHAReassessment, user: AuthenticatedUser
) -> FieldRecordRead:
    source = _require_flha(db, record_id)
    profile = _authorize_edit(db, source, user)
    _validate_crew(db, payload.details)
    blockers = _blockers(payload.details)
    old = source.details or {}
    version = int(old.get("flha_version") or 1) + 1
    root_id = UUID(str(old.get("root_record_id") or source.id))
    details = _details_payload(
        payload.details,
        user=user,
        version=version,
        source_record_id=source.id,
        root_record_id=root_id,
        reason=payload.reason,
        action="reassessed",
    )
    details["release_blockers"] = blockers
    item = FieldRecord(
        record_type=source.record_type,
        project_id=source.project_id,
        employee_id=profile.id if profile else source.employee_id,
        work_date=source.work_date,
        title=source.title,
        status="blocked" if blockers else "draft",
        severity="critical" if blockers else "none",
        details=details,
        document_ids=[],
        signatures=[],
        alert_recipients=[],
        submitted_by=user.email,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _schema(item)


def suggest_controls(payload: FLHASuggestionRequest) -> list[FLHASuggestion]:
    task = payload.task.casefold()
    if any(word in task for word in ("excavat", "trench", "utility")):
        return [
            FLHASuggestion(
                hazard="Cave-in or utility strike",
                control="Verify current locates, protective system, spoil setback and safe access in the field.",
                control_hierarchy="engineering",
            )
        ]
    if any(word in task for word in ("traffic", "road", "lane")):
        return [
            FLHASuggestion(
                hazard="Worker or equipment struck by traffic",
                control="Use the approved traffic-control plan, trained traffic-control persons and verified devices.",
                control_hierarchy="administrative",
            )
        ]
    return [
        FLHASuggestion(
            hazard="Changing site conditions or worker-equipment interaction",
            control="Inspect the work area, confirm communication and stop work if the planned control is not effective.",
            control_hierarchy="administrative",
        )
    ]


def presets() -> list[dict]:
    return PRESETS


def _pdf_escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_pages(lines: list[str]) -> bytes:
    chunks = [lines[index:index + 55] for index in range(0, len(lines), 55)] or [["FLHA record"]]
    objects: list[bytes] = []
    page_ids: list[int] = []
    font_id = 3 + len(chunks) * 2
    for index, chunk in enumerate(chunks):
        page_id = 3 + index * 2
        content_id = page_id + 1
        page_ids.append(page_id)
        commands = ["BT", "/F1 8 Tf", "36 756 Td", "10 TL"]
        for line in chunk:
            commands.append(f"({_pdf_escape(line[:112])}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode()
        objects.extend(
            [
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode(),
                b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            ]
        )
    ordered = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>".encode(),
        *objects,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, body in enumerate(ordered, start=1):
        offsets.append(output.tell())
        output.write(f"{object_id} 0 obj\n".encode())
        output.write(body)
        output.write(b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(ordered) + 1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(
        f"trailer\n<< /Size {len(ordered) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return output.getvalue()


def export_flha_pdf(db: Session, record_id: UUID, user: AuthenticatedUser) -> bytes:
    item = _require_flha(db, record_id)
    _authorize_read(db, item, user)
    details = item.details or {}
    project = db.get(Project, item.project_id)
    lines = [
        "IRON HOUSE CIVIL CONSTRUCTORS - FIELD LEVEL HAZARD ASSESSMENT",
        f"Project: {project.name if project else item.project_id} | Site: {details.get('site_location', '')}",
        f"Date: {item.work_date} | Version: {details.get('flha_version', 1)} | Status: {item.status.upper()}",
        f"Supervisor: {details.get('supervisor_name', '')} | First aid: {details.get('first_aid_attendant', '')}",
        f"Weather: {details.get('weather', '')}",
        "",
        "TASK | HAZARD | CONTROL | RESPONSIBLE | HIERARCHY",
    ]
    for row in details.get("tasks", []):
        lines.append(
            " | ".join(
                [
                    str(row.get("task", "")),
                    str(row.get("hazard", "")),
                    str(row.get("control", "")),
                    str(row.get("responsible_person", "")),
                    str(row.get("control_hierarchy", "")).upper(),
                ]
            )
        )
    lines.extend(
        [
            "",
            f"Emergency response: {details.get('emergency_response', '')}",
            f"Muster point: {details.get('muster_point', '')}",
            f"Communication: {details.get('communication_method', '')}",
            "Stop work: " + "; ".join(details.get("stop_work_triggers", [])),
            "",
            "CREW ACKNOWLEDGEMENTS (each row kept intact)",
        ]
    )
    signatures = {entry.get("employee_id"): entry for entry in (item.signatures or [])}
    for member in details.get("crew", []):
        signature = signatures.get(str(member.get("employee_id")))
        lines.append(
            f"{member.get('employee_name')} | "
            + (f"Signed {signature.get('signed_at')} by {signature.get('signed_by_account')}" if signature else "Pending signature")
        )
    lines.extend(
        [
            "",
            f"Released by: {details.get('released_by', 'Not released')}",
            "AI suggestions are advisory only and never mark an FLHA safe or complete.",
        ]
    )
    return _pdf_pages(lines)

