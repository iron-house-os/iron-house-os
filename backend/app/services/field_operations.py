from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import textwrap
import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.equipment import Equipment
from app.models.bid import Bid
from app.models.field_operations import EmployeeCertification, FieldRecord, TimeEntry, Vehicle, VehicleLog
from app.models.project import Project
from app.models.supplier import Supplier
from app.models.user import Employee, UserAccount
from app.schemas.field_operations import (
    CertificationCreate,
    CertificationRead,
    EmployeeCreate,
    EmployeeRead,
    FieldOperationsBootstrap,
    FieldRecordCreate,
    FieldRecordRead,
    FieldRecordUpdate,
    FLHAReassessmentCreate,
    FLHAReleaseCreate,
    MilestoneDecision,
    SignatureCreate,
    TimeOffDecision,
    TimeEntryCreate,
    TimeEntryRead,
    ToolboxTalk,
    VehicleCreate,
    VehicleLogCreate,
    VehicleLogRead,
    VehicleRead,
    VehicleUpdate,
)
from app.services.auth import AuthenticatedUser, hash_password
from app.services.cost_codes import get_cost_code_library


MANAGEMENT_ALERT_RECIPIENTS = ["Jeremie Peters", "Mac Warren"]
MATERIAL_TYPES = [
    {"code": "pit_run", "name": "Pit run gravel"},
    {"code": "75mm_minus", "name": "75 mm minus"},
    {"code": "50mm_minus", "name": "50 mm minus"},
    {"code": "25mm_minus", "name": "25 mm minus"},
    {"code": "19mm_minus", "name": "19 mm minus / road base"},
    {"code": "19mm_clear", "name": "19 mm clear crush"},
    {"code": "13mm_clear", "name": "13 mm clear crush"},
    {"code": "10mm_screenings", "name": "10 mm screenings"},
    {"code": "pea_gravel", "name": "Pea gravel"},
    {"code": "drain_rock", "name": "Drain rock"},
    {"code": "bedding_sand", "name": "Bedding sand"},
    {"code": "concrete_sand", "name": "Concrete sand"},
    {"code": "riprap", "name": "Riprap"},
    {"code": "structural_fill", "name": "Structural fill"},
    {"code": "native_material", "name": "Native material"},
    {"code": "topsoil", "name": "Topsoil"},
    {"code": "other", "name": "Other material"},
]
MILESTONE_CATALOG = [
    {"id": "civil_green_hat_rookie", "track": "civil", "name": "Green Hat Rookie", "minimum_months": 0, "practical": ["Completes site orientation", "Identifies basic hazards and controls", "Uses PPE and follows supervisor direction"]},
    {"id": "civil_probation_complete", "track": "civil", "name": "3-Month Probation Complete", "minimum_months": 3, "practical": ["Completes assigned work safely", "Uses tools correctly", "Communicates hazards and progress"]},
    {"id": "civil_labourer", "track": "civil", "name": "Labourer — Green Hat Removed", "minimum_months": 8, "practical": ["Works independently on routine tasks", "Supports excavation and backfill", "Maintains housekeeping and paperwork"]},
    {"id": "civil_skilled_labourer", "track": "civil", "name": "Skilled Labourer", "minimum_months": 8, "practical": ["Reads grades and measurements", "Supports compaction and utility installation", "Anticipates crew needs safely"]},
    {"id": "civil_rookie_pipe", "track": "civil", "name": "Rookie Pipe Layer", "minimum_months": 8, "practical": ["Identifies pipe and fittings", "Prepares bedding and joints", "Checks line, grade and cleanliness"]},
    {"id": "civil_senior_pipe", "track": "civil", "name": "Senior Pipe Layer / Ditch Boss", "minimum_months": 8, "practical": ["Directs safe trench workflow", "Verifies line, grade and connections", "Coordinates operator and top person"]},
    {"id": "civil_topman_grademan", "track": "civil", "name": "Top Man / Grademan", "minimum_months": 8, "practical": ["Sets and checks grade controls", "Calculates cuts and fills", "Documents quantities and changes"]},
    {"id": "civil_junior_foreman", "track": "civil", "name": "Junior Foreman", "minimum_months": 8, "practical": ["Plans daily work and crew assignments", "Leads hazard assessments", "Completes cost-coded paperwork on time"]},
    {"id": "civil_foreman", "track": "civil", "name": "Foreman", "minimum_months": 8, "practical": ["Leads production, safety and quality", "Coordinates vendors and management", "Coaches and assesses crew competency"]},
    {"id": "operator_green_hat", "track": "operator", "name": "Green Hat Operator", "minimum_months": 0, "practical": ["Completes pre-use inspection", "Demonstrates safe start, travel and shutdown", "Maintains exclusion zones"]},
    {"id": "operator_service_hoe", "track": "operator", "name": "Service Hoe Operator", "minimum_months": 3, "practical": ["Excavates safely around services", "Uses spotter communication", "Maintains depth and trench control"]},
    {"id": "operator_mainline", "track": "operator", "name": "Mainline Operator", "minimum_months": 8, "practical": ["Maintains production line and grade", "Loads trucks efficiently with minimal spillage", "Coordinates safely with pipe crew"]},
    {"id": "operator_fine_finish", "track": "operator", "name": "Fine Finish Operator", "minimum_months": 8, "practical": ["Finishes to design tolerance", "Reads grade stakes and instruments", "Protects completed work and adjacent assets"]},
]
MILESTONE_QUESTIONS = {
    "civil": [
        {"id": "hazard", "prompt": "What should happen before a task starts when a hazard is not controlled?", "options": ["Continue carefully", "Stop and establish controls", "Wait until lunch"], "answer": 1},
        {"id": "grade", "prompt": "What confirms pipe or excavation elevation is being built correctly?", "options": ["Line and grade checks", "Truck count", "Fuel usage"], "answer": 0},
        {"id": "paperwork", "prompt": "When should daily field paperwork be complete?", "options": ["Before the next workday", "At month end", "Only when requested"], "answer": 0},
        {"id": "utility", "prompt": "Before excavating near a known utility, the crew must first:", "options": ["Increase bucket speed", "Confirm location and controls", "Remove the spotter"], "answer": 1},
        {"id": "compaction", "prompt": "Compaction quality depends on using the specified material, lift thickness and:", "options": ["Moisture and compaction effort", "Paint colour", "Truck model"], "answer": 0},
    ],
    "operator": [
        {"id": "inspection", "prompt": "What is required before operating equipment?", "options": ["Pre-use inspection", "Production photo only", "Fuel receipt"], "answer": 0},
        {"id": "stability", "prompt": "The operator must continually assess machine stability, excavation edges and:", "options": ["Soil conditions", "Radio volume", "Paint condition"], "answer": 0},
        {"id": "signals", "prompt": "If the operator loses sight of the designated spotter, the operator should:", "options": ["Continue slowly", "Stop movement", "Sound the horn and continue"], "answer": 1},
        {"id": "loading", "prompt": "Efficient truck loading should minimize spillage and maintain:", "options": ["A level clean floor", "Maximum swing speed", "An unmarked exclusion zone"], "answer": 0},
        {"id": "shutdown", "prompt": "When work pauses, implements should be:", "options": ["Left raised", "Lowered safely", "Held over the trench"], "answer": 1},
    ],
}


def get_bootstrap(db: Session, user: AuthenticatedUser) -> FieldOperationsBootstrap:
    employees = list(db.scalars(select(Employee).order_by(Employee.last_name, Employee.first_name)))
    profile = next((item for item in employees if item.email.lower() == user.email.lower()), None)
    field_role = profile.portal_role if profile else None
    projects = list(db.scalars(select(Project).order_by(Project.name)))
    suppliers = list(db.scalars(select(Supplier).order_by(Supplier.name)))
    equipment = list(db.scalars(select(Equipment).order_by(Equipment.name)))
    vehicles = list(db.scalars(select(Vehicle).order_by(Vehicle.unit_number)))
    vehicle_logs = list(db.scalars(select(VehicleLog).order_by(VehicleLog.entry_date.desc()).limit(100)))
    time_entries = list(db.scalars(select(TimeEntry).order_by(TimeEntry.work_date.desc()).limit(200)))
    records = list(db.scalars(select(FieldRecord).order_by(FieldRecord.work_date.desc(), FieldRecord.created_at.desc()).limit(200)))
    certifications = list(db.scalars(select(EmployeeCertification).order_by(EmployeeCertification.expiry_date)))
    workbooks, production_items = build_job_workbooks(db)
    material_movement_summary = build_material_movement_summary(db)
    milestone_recognitions = build_milestone_recognitions(db)
    paperwork_recognitions = build_paperwork_recognitions(db, employees)
    if user.role == "viewer" and field_role in {"employee", "operator"}:
        employee_id = profile.id if profile else None
        employees = [profile] if profile else []
        time_entries = [item for item in time_entries if item.employee_id == employee_id]
        records = [item for item in records if item.employee_id == employee_id or item.record_type == "toolbox_talk"]
        certifications = [item for item in certifications if item.employee_id == employee_id]
        milestone_recognitions = [item for item in milestone_recognitions if item["employee_id"] == str(employee_id)]
        paperwork_recognitions = [item for item in paperwork_recognitions if item["employee_id"] == str(employee_id)]
    alerts = build_alerts(vehicles, records, certifications)
    return FieldOperationsBootstrap(
        employees=[EmployeeRead.model_validate(item) for item in employees],
        projects=[{"id": str(item.id), "name": item.name, "project_number": item.project_number, "status": item.status} for item in projects],
        suppliers=[{"id": str(item.id), "name": item.name, "category": item.category} for item in suppliers],
        equipment=[{"id": str(item.id), "name": item.name, "identifier": item.identifier, "status": item.status} for item in equipment],
        cost_codes=[item.model_dump(mode="json") for item in get_cost_code_library().items],
        job_workbooks=workbooks,
        production_items=production_items,
        material_types=MATERIAL_TYPES,
        material_movement_summary=material_movement_summary,
        milestone_catalog=public_milestone_catalog(),
        milestone_recognitions=milestone_recognitions,
        paperwork_recognitions=paperwork_recognitions,
        vehicles=[vehicle_schema(item) for item in vehicles],
        vehicle_logs=[VehicleLogRead.model_validate(item) for item in vehicle_logs],
        time_entries=[TimeEntryRead.model_validate(item) for item in time_entries],
        records=[FieldRecordRead.model_validate(item) for item in records],
        certifications=[certification_schema(item) for item in certifications],
        alerts=alerts,
        toolbox_talk=current_toolbox_talk(),
    )


def public_milestone_catalog() -> list[dict]:
    return [
        {**item, "written_questions": [{"id": q["id"], "prompt": q["prompt"], "options": q["options"]} for q in MILESTONE_QUESTIONS[item["track"]]]}
        for item in MILESTONE_CATALOG
    ]


def build_milestone_recognitions(db: Session) -> list[dict]:
    records = db.scalars(select(FieldRecord).where(
        FieldRecord.record_type == "milestone_review", FieldRecord.status == "approved"
    ).order_by(FieldRecord.updated_at.desc()))
    return [{
        "record_id": str(item.id), "employee_id": str(item.employee_id),
        "employee_name": (item.details or {}).get("employee_name"),
        "milestone_name": (item.details or {}).get("milestone_name"),
        "approved_at": (item.details or {}).get("approved_at"),
        "reward_type": (item.details or {}).get("reward_type", "none"),
        "reward_description": (item.details or {}).get("reward_description"),
    } for item in records]


def build_paperwork_recognitions(db: Session, employees: list[Employee]) -> list[dict]:
    names = {item.id: f"{item.first_name} {item.last_name}" for item in employees}
    entries = db.scalars(select(TimeEntry).order_by(TimeEntry.work_date))
    days: dict[UUID, set[date]] = {}
    for item in entries:
        if item.created_at.date() <= item.work_date:
            days.setdefault(item.employee_id, set()).add(item.work_date)
    records = db.scalars(select(FieldRecord).where(FieldRecord.employee_id.is_not(None)).order_by(FieldRecord.work_date))
    for item in records:
        if item.employee_id and item.created_at.date() <= item.work_date:
            days.setdefault(item.employee_id, set()).add(item.work_date)
    return [{"employee_id": str(employee_id), "employee_name": names.get(employee_id, "Employee"), "on_time_days": len(work_days)} for employee_id, work_days in days.items() if work_days]


def build_material_movement_summary(db: Session) -> list[dict]:
    records = db.scalars(
        select(FieldRecord).where(FieldRecord.record_type == "material_movement")
    )
    totals: dict[tuple[str, str, str], dict] = {}
    for record in records:
        details = record.details or {}
        direction = str(details.get("direction") or "")
        material_code = str(details.get("material_code") or "other")
        material_type = str(details.get("material_type") or "Other material")
        key = (str(record.project_id or ""), direction, material_code)
        item = totals.setdefault(key, {
            "project_id": str(record.project_id) if record.project_id else None,
            "direction": direction,
            "material_code": material_code,
            "material_type": material_type,
            "loads": 0.0,
            "total_tonnes": 0.0,
        })
        try:
            item["loads"] += float(details.get("loads") or 0)
            item["total_tonnes"] += float(details.get("total_tonnes") or 0)
        except (TypeError, ValueError):
            continue
    return sorted(totals.values(), key=lambda item: (item["project_id"] or "", item["material_type"], item["direction"]))


def build_job_workbooks(db: Session) -> tuple[list[dict], list[dict]]:
    bids = list(db.scalars(select(Bid).order_by(Bid.project_id, Bid.created_at.desc())))
    latest: dict[UUID, Bid] = {}
    for bid in bids:
        if bid.project_id not in latest and (bid.bid_json or {}).get("source") == "estimate_workspace":
            latest[bid.project_id] = bid

    production_records = db.scalars(
        select(FieldRecord).where(FieldRecord.record_type == "material_quantity")
    )
    installed: dict[str, float] = {}
    for record in production_records:
        line_key = str((record.details or {}).get("line_key") or "")
        try:
            quantity = float((record.details or {}).get("installed_quantity") or 0)
        except (TypeError, ValueError):
            quantity = 0
        if line_key:
            installed[line_key] = installed.get(line_key, 0) + quantity

    workbooks: list[dict] = []
    production_items: list[dict] = []
    for project_id, bid in latest.items():
        estimate = (bid.bid_json or {}).get("estimate") or {}
        lines = estimate.get("line_items") or []
        workbooks.append({
            "id": str(bid.id),
            "project_id": str(project_id),
            "status": bid.status,
            "created_at": bid.created_at.isoformat(),
            "line_count": len(lines),
        })
        for index, line in enumerate(lines):
            line_key = f"{bid.id}:{index}"
            estimated = float(line.get("quantity") or 0)
            installed_quantity = installed.get(line_key, 0)
            production_items.append({
                "line_key": line_key,
                "workbook_id": str(bid.id),
                "project_id": str(project_id),
                "cost_code": line.get("code"),
                "description": line.get("description") or f"Line {index + 1}",
                "unit": line.get("unit") or "lump_sum",
                "estimated_quantity": estimated,
                "installed_quantity": installed_quantity,
                "remaining_quantity": max(estimated - installed_quantity, 0),
                "percent_complete": round(min(installed_quantity / estimated * 100, 100), 1) if estimated else 0,
                "materials": line.get("materials") or [],
            })
    return workbooks, production_items


def create_employee(db: Session, payload: EmployeeCreate, user: AuthenticatedUser) -> EmployeeRead:
    if user.role not in {"admin", "operations_manager"}:
        raise AppError("Management access is required to create employees.", status_code=403)
    item = Employee(**payload.model_dump(), status="active")
    db.add(item)
    commit(db, "An employee with that email already exists.")
    db.refresh(item)
    temporary_password = payload.temporary_password or secrets.token_urlsafe(14)
    access_created = False
    if payload.provision_portal_access and db.scalar(select(UserAccount).where(UserAccount.email.ilike(item.email))) is None:
        db.add(UserAccount(email=item.email.lower(), display_name=f"{item.first_name} {item.last_name}", role="viewer", password_hash=hash_password(temporary_password), is_active=True, password_reset_required=True))
        commit(db)
        access_created = True
    return EmployeeRead.model_validate(item).model_copy(update={"portal_access_created": access_created, "temporary_password": temporary_password if access_created else None})


def create_certification(db: Session, payload: CertificationCreate) -> CertificationRead:
    require_exists(db, Employee, payload.employee_id, "Employee")
    item = EmployeeCertification(**payload.model_dump())
    db.add(item)
    commit(db)
    db.refresh(item)
    return certification_schema(item)


def create_vehicle(db: Session, payload: VehicleCreate) -> VehicleRead:
    item = Vehicle(**payload.model_dump())
    db.add(item)
    commit(db, "That vehicle unit number or VIN already exists.")
    db.refresh(item)
    return vehicle_schema(item)


def update_vehicle(db: Session, vehicle_id: UUID, payload: VehicleUpdate) -> VehicleRead:
    item = require_exists(db, Vehicle, vehicle_id, "Vehicle")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.add(item)
    commit(db)
    db.refresh(item)
    return vehicle_schema(item)


def create_vehicle_log(db: Session, payload: VehicleLogCreate) -> VehicleLogRead:
    vehicle = require_exists(db, Vehicle, payload.vehicle_id, "Vehicle")
    values = payload.model_dump()
    values["document_ids"] = [str(document_id) for document_id in payload.document_ids]
    item = VehicleLog(**values)
    db.add(item)
    if payload.odometer_km is not None and payload.odometer_km >= vehicle.current_km:
        vehicle.current_km = payload.odometer_km
        db.add(vehicle)
    commit(db)
    db.refresh(item)
    return VehicleLogRead.model_validate(item)


def create_time_entry(db: Session, payload: TimeEntryCreate, user: AuthenticatedUser) -> TimeEntryRead:
    employee = require_exists(db, Employee, payload.employee_id, "Employee")
    profile = db.scalar(select(Employee).where(Employee.email.ilike(user.email)))
    if user.role == "viewer" and (profile is None or (profile.portal_role != "foreman" and employee.id != profile.id)):
        raise AppError("You can only submit time for your own employee profile.", status_code=403)
    require_exists(db, Project, payload.project_id, "Project")
    item = TimeEntry(**payload.model_dump(), status="submitted", submitted_by=user.email)
    db.add(item)
    commit(db)
    db.refresh(item)
    return TimeEntryRead.model_validate(item)


FLHA_REQUIRED_SCREENINGS = {
    "first_aid_equipment", "overhead_hazards", "underground_utilities_locates",
    "mobile_equipment", "confined_space", "excavation_protection_access",
    "additional_ppe", "traffic_control", "subcontractors", "basic_ppe_review",
}
FLHA_HIERARCHY = {"elimination", "substitution", "engineering", "administrative", "ppe"}


def _audit(details: dict, action: str, user: AuthenticatedUser, **metadata: object) -> dict:
    events = list(details.get("audit") or [])
    events.append({
        "action": action, "at": datetime.now(UTC).isoformat(), "actor": user.email,
        "actor_name": user.display_name, **metadata,
    })
    return {**details, "audit": events}


def _crew_ids(details: dict) -> set[str]:
    return {
        str(entry.get("employee_id") or entry.get("id"))
        for entry in (details.get("crew") or [])
        if isinstance(entry, dict) and (entry.get("employee_id") or entry.get("id"))
    }


def _flha_blockers(project_id: UUID | None, details: dict) -> list[str]:
    blockers: list[str] = []
    required = {
        "project / job": project_id, "site / location": details.get("site_location"),
        "supervisor / foreperson": details.get("supervisor"),
        "first aid attendant": details.get("first_aid_attendant"),
        "crew": details.get("crew"), "weather": details.get("weather"),
    }
    blockers.extend(f"Missing {label}" for label, value in required.items() if not value)
    if details.get("crew") and not _crew_ids(details):
        blockers.append("Crew entries must identify an employee")
    screenings = details.get("screenings") or {}
    missing_screenings = sorted(FLHA_REQUIRED_SCREENINGS - set(screenings))
    if missing_screenings or any(screenings.get(key) not in {"yes", "no", "na"} for key in FLHA_REQUIRED_SCREENINGS):
        blockers.append("Complete every Yes / No / N/A screening item")
    emergency = details.get("emergency") or {}
    for key, label in (("muster_point", "muster point"), ("first_aid", "first aid response"), ("communication", "emergency communication"), ("stop_work_triggers", "stop-work triggers")):
        if not emergency.get(key):
            blockers.append(f"Missing {label}")
    rows = details.get("tasks") or []
    if not rows:
        blockers.append("Add at least one task, hazard and control row")
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            blockers.append(f"Task row {index} is invalid")
            continue
        if not all(str(row.get(key) or "").strip() for key in ("task", "hazard", "control", "responsible_person")):
            blockers.append(f"Task row {index} is incomplete")
        if row.get("control_type") not in FLHA_HIERARCHY:
            blockers.append(f"Task row {index} needs a hierarchy-of-controls category")
        if row.get("critical") and (not row.get("control_accepted") or not row.get("responsible_person") or (row.get("evidence_required") and not row.get("evidence"))):
            blockers.append(f"Critical hazard in task row {index} is uncontrolled")
    return list(dict.fromkeys(blockers))


def _prepare_flha(project_id: UUID | None, details: dict, user: AuthenticatedUser, action: str) -> tuple[dict, str]:
    prepared = dict(details)
    prepared.setdefault("version", 1)
    prepared["blockers"] = _flha_blockers(project_id, prepared)
    prepared["release_state"] = "blocked" if prepared["blockers"] else "draft"
    prepared = _audit(prepared, action, user, release_state=prepared["release_state"])
    return prepared, "blocked" if prepared["blockers"] else "draft"


def create_field_record(db: Session, payload: FieldRecordCreate, user: AuthenticatedUser) -> FieldRecordRead:
    if payload.project_id:
        require_exists(db, Project, payload.project_id, "Project")
    if payload.employee_id:
        require_exists(db, Employee, payload.employee_id, "Employee")
    alerts = payload.alert_recipients
    if payload.severity in {"medium", "high", "critical"} and not alerts:
        alerts = MANAGEMENT_ALERT_RECIPIENTS
    values = payload.model_dump()
    profile = db.scalar(select(Employee).where(Employee.email.ilike(user.email)))
    if user.role == "viewer":
        if profile is None:
            raise AppError("Your employee profile is not linked to this account.", status_code=400)
        if payload.record_type == "crew_shift" and profile.portal_role != "foreman":
            raise AppError("Foreman access is required to schedule crews.", status_code=403)
        if profile.portal_role in {"employee", "operator"}:
            if payload.employee_id and payload.employee_id != profile.id:
                raise AppError("You can only create records for your own employee profile.", status_code=403)
            values["employee_id"] = profile.id
    if payload.record_type == "daily_hazard_assessment":
        if user.role == "viewer" and (profile is None or profile.portal_role != "foreman"):
            raise AppError("Foreperson or management access is required to create an FLHA.", status_code=403)
        values["details"], values["status"] = _prepare_flha(
            payload.project_id, payload.details, user, "created",
        )
    if payload.record_type == "crew_shift":
        values["status"] = "scheduled"
        values["details"] = {**payload.details, "scheduled_by": user.display_name, "scheduled_at": datetime.now(UTC).isoformat()}
    if payload.record_type == "time_off_request":
        if profile is None and not payload.employee_id:
            raise AppError("Select an employee for the time-off request.", status_code=400)
        values["employee_id"] = values.get("employee_id") or profile.id
        values["status"] = "pending"
        values["details"] = {**payload.details, "requested_by": user.display_name, "requested_at": datetime.now(UTC).isoformat()}
    if payload.record_type == "milestone_review":
        employee = require_exists(db, Employee, payload.employee_id, "Employee") if payload.employee_id else db.scalar(
            select(Employee).where(Employee.email.ilike(user.email))
        )
        if employee is None:
            raise AppError("Your employee profile is not linked to this account.", status_code=400)
        if user.role not in {"admin", "operations_manager"} and employee.email.lower() != user.email.lower():
            raise AppError("You can only request your own milestone review.", status_code=403)
        milestone_id = str(payload.details.get("milestone_id") or "")
        milestone = next((item for item in MILESTONE_CATALOG if item["id"] == milestone_id), None)
        if milestone is None:
            raise AppError("Select a valid milestone.", status_code=400)
        answers = payload.details.get("written_answers") or {}
        questions = MILESTONE_QUESTIONS[milestone["track"]]
        correct = sum(1 for question in questions if answers.get(question["id"]) == question["answer"])
        score = round(correct / len(questions) * 100)
        values["employee_id"] = employee.id
        values["status"] = "practical_pending" if score >= 80 else "written_retry_required"
        values["details"] = {
            **payload.details,
            "employee_name": f"{employee.first_name} {employee.last_name}",
            "milestone_name": milestone["name"],
            "track": milestone["track"],
            "written_score": score,
            "written_passed": score >= 80,
            "practical_status": "pending",
            "requested_at": datetime.now(UTC).isoformat(),
        }
    values["document_ids"] = [str(document_id) for document_id in payload.document_ids]
    values["alert_recipients"] = alerts
    item = FieldRecord(**values, submitted_by=user.email)
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def _require_flha(record: FieldRecord) -> None:
    if record.record_type != "daily_hazard_assessment":
        raise AppError("That record is not an FLHA.", status_code=400)


def _can_supervise_flha(db: Session, user: AuthenticatedUser) -> bool:
    if user.role in {"admin", "operations_manager"}:
        return True
    profile = db.scalar(select(Employee).where(Employee.email.ilike(user.email)))
    return bool(profile and profile.portal_role == "foreman")


def update_field_record(
    db: Session, record_id: UUID, payload: FieldRecordUpdate, user: AuthenticatedUser,
) -> FieldRecordRead:
    item = require_exists(db, FieldRecord, record_id, "Field record")
    _require_flha(item)
    if not _can_supervise_flha(db, user):
        raise AppError("Foreperson or management access is required to edit an FLHA.", status_code=403)
    if item.signatures or item.status == "released":
        raise AppError("Signed FLHAs are immutable. Create a re-assessment instead.", status_code=409)
    values = payload.model_dump(exclude_unset=True)
    if "details" in values:
        details = {**(item.details or {}), **(values.pop("details") or {})}
        details, item.status = _prepare_flha(item.project_id, details, user, "edited")
        item.details = details
    else:
        item.details = _audit(item.details or {}, "edited", user)
    for key, value in values.items():
        if key == "document_ids":
            value = [str(document_id) for document_id in value]
        setattr(item, key, value)
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def reassess_flha(
    db: Session, record_id: UUID, payload: FLHAReassessmentCreate, user: AuthenticatedUser,
) -> FieldRecordRead:
    previous = require_exists(db, FieldRecord, record_id, "FLHA")
    _require_flha(previous)
    if not _can_supervise_flha(db, user):
        raise AppError("Foreperson or management access is required to re-assess an FLHA.", status_code=403)
    details = {**(previous.details or {}), **(payload.details or {})}
    details.pop("release", None)
    details.pop("frozen_sha256", None)
    details["version"] = int((previous.details or {}).get("version") or 1) + 1
    details["previous_version_id"] = str(previous.id)
    details["change_reason"] = payload.change_reason
    details["changed_conditions"] = payload.changed_conditions
    details["audit"] = []
    details, next_status = _prepare_flha(previous.project_id, details, user, "reassessed")
    item = FieldRecord(
        record_type=previous.record_type, project_id=previous.project_id, employee_id=previous.employee_id,
        cost_code=previous.cost_code, work_date=date.today(), title=previous.title, status=next_status,
        severity=previous.severity, details=details, document_ids=list(previous.document_ids or []),
        signatures=[], alert_recipients=list(previous.alert_recipients or []), submitted_by=user.email,
    )
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def release_flha(
    db: Session, record_id: UUID, payload: FLHAReleaseCreate, user: AuthenticatedUser,
) -> FieldRecordRead:
    item = require_exists(db, FieldRecord, record_id, "FLHA")
    _require_flha(item)
    if not _can_supervise_flha(db, user):
        raise AppError("Foreperson or management access is required to release an FLHA.", status_code=403)
    if item.status == "released":
        raise AppError("This FLHA version is already released.", status_code=409)
    if not payload.field_conditions_verified:
        raise AppError("The responsible field person must verify actual work-location conditions.", status_code=400)
    base_blockers = _flha_blockers(item.project_id, item.details or {})
    blockers = list(base_blockers)
    crew = _crew_ids(item.details or {})
    signed = {str(entry.get("employee_id")) for entry in (item.signatures or [])}
    if crew - signed:
        blockers.append("Every listed worker must review and sign this version")
    if blockers:
        details = {**(item.details or {}), "blockers": blockers, "release_state": "blocked"}
        item.details = _audit(details, "release_blocked", user, blockers=blockers)
        item.status = "blocked" if base_blockers else "draft"
        db.add(item)
        commit(db)
        raise AppError("FLHA release blocked: " + "; ".join(blockers), status_code=409)
    released_at = datetime.now(UTC).isoformat()
    frozen = {
        **(item.details or {}),
        "release_state": "released",
        "blockers": [],
        "release": {
            "supervisor_name": payload.supervisor_name, "released_by": user.email,
            "released_at": released_at, "acknowledgement": payload.acknowledgement,
        },
    }
    snapshot = {"title": item.title, "details": frozen, "signatures": item.signatures, "documents": item.document_ids}
    frozen["frozen_sha256"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()
    item.details = _audit(frozen, "supervisor_released", user, supervisor=payload.supervisor_name)
    item.status = "released"
    item.resolved_at = datetime.now(UTC)
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def _pdf_escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _simple_pdf(lines: list[str]) -> bytes:
    wrapped = [part for line in lines for part in (textwrap.wrap(str(line), width=92) or [""])]
    pages = [wrapped[index:index + 54] for index in range(0, len(wrapped), 54)] or [[""]]
    objects: list[bytes] = [b"", b""]
    font_id = 3 + len(pages) * 2
    page_ids: list[int] = []
    for page_lines in pages:
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_ids.append(page_id)
        stream = "BT /F1 9 Tf 42 756 Td 11 TL " + " ".join(f"({_pdf_escape(line)}) Tj T*" for line in page_lines) + " ET"
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode())
        objects.append(f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream".encode())
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)


def export_flha_pdf(db: Session, record_id: UUID, user: AuthenticatedUser) -> bytes:
    item = require_exists(db, FieldRecord, record_id, "FLHA")
    _require_flha(item)
    details = item.details or {}
    if user.role == "viewer":
        profile = db.scalar(select(Employee).where(Employee.email.ilike(user.email)))
        crew_ids = _crew_ids(details)
        if profile is None or (profile.portal_role != "foreman" and str(profile.id) not in crew_ids):
            raise AppError("You do not have access to this FLHA.", status_code=403)
    lines = [
        "IRON HOUSE - FIELD LEVEL HAZARD ASSESSMENT",
        f"{item.title} | Date: {item.work_date} | Version: {details.get('version', 1)} | Status: {item.status.upper()}",
        f"Site: {details.get('site_location', '')} | Supervisor: {details.get('supervisor', '')} | Weather: {details.get('weather', '')}",
        "", "TASK | HAZARD | CONTROL (HIERARCHY) | RESPONSIBLE",
    ]
    for row in details.get("tasks") or []:
        lines.append(f"{row.get('task', '')} | {row.get('hazard', '')} | {row.get('control', '')} ({row.get('control_type', '')}) | {row.get('responsible_person', '')}")
    emergency = details.get("emergency") or {}
    lines.extend([
        "", "EMERGENCY RESPONSE",
        f"Muster: {emergency.get('muster_point', '')} | First aid: {emergency.get('first_aid', '')}",
        f"Communication: {emergency.get('communication', '')} | Stop work: {emergency.get('stop_work_triggers', '')}",
        "", "CREW ACKNOWLEDGEMENTS",
    ])
    for signature in item.signatures or []:
        lines.append(f"{signature.get('employee_name')} | {signature.get('signed_at')} | {signature.get('signing_mode', 'own_device')}")
    release = details.get("release") or {}
    lines.extend(["", f"Supervisor release: {release.get('supervisor_name', 'Not released')} | {release.get('released_at', '')}", f"Audit events: {len(details.get('audit') or [])} | Attachments: {len(item.document_ids or [])}"])
    return _simple_pdf(lines)


def decide_time_off(
    db: Session,
    record_id: UUID,
    payload: TimeOffDecision,
    user: AuthenticatedUser,
) -> FieldRecordRead:
    if user.role not in {"admin", "operations_manager"}:
        raise AppError("Management access is required for time-off decisions.", status_code=403)
    item = require_exists(db, FieldRecord, record_id, "Time-off request")
    if item.record_type != "time_off_request":
        raise AppError("That record is not a time-off request.", status_code=400)
    if item.status != "pending":
        raise AppError("That time-off request has already been decided.", status_code=409)
    item.status = payload.decision
    item.details = {
        **(item.details or {}),
        "management_notes": payload.management_notes,
        "decision_by": user.display_name,
        "decision_at": datetime.now(UTC).isoformat(),
    }
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def decide_milestone(
    db: Session,
    record_id: UUID,
    payload: MilestoneDecision,
    user: AuthenticatedUser,
) -> FieldRecordRead:
    if user.role not in {"admin", "operations_manager"}:
        raise AppError("Management access is required for milestone decisions.", status_code=403)
    item = require_exists(db, FieldRecord, record_id, "Milestone review")
    if item.record_type != "milestone_review":
        raise AppError("That record is not a milestone review.", status_code=400)
    details = dict(item.details or {})
    if payload.decision == "approved" and (not details.get("written_passed") or not payload.practical_passed):
        raise AppError("Written and practical assessments must both pass before approval.", status_code=400)
    details.update({
        "practical_status": "passed" if payload.practical_passed else "not_passed",
        "practical_notes": payload.practical_notes,
        "decision_by": user.display_name,
        "decision_at": datetime.now(UTC).isoformat(),
        "reward_type": payload.reward_type,
        "reward_description": payload.reward_description,
    })
    if payload.decision == "approved":
        details["approved_at"] = details["decision_at"]
    item.details = details
    item.status = payload.decision
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def sign_field_record(
    db: Session,
    record_id: UUID,
    payload: SignatureCreate,
    user: AuthenticatedUser,
) -> FieldRecordRead:
    item = require_exists(db, FieldRecord, record_id, "Field record")
    employee = require_exists(db, Employee, payload.employee_id, "Employee")
    is_flha = item.record_type == "daily_hazard_assessment"
    if is_flha:
        if item.status == "released":
            raise AppError("Released FLHAs are immutable.", status_code=409)
        if item.status == "blocked":
            raise AppError("Resolve all FLHA blockers before collecting signatures.", status_code=409)
        crew = _crew_ids(item.details or {})
        if str(employee.id) not in crew:
            raise AppError("Only workers listed on this FLHA may sign it.", status_code=403)
        own_account = employee.email.lower() == user.email.lower()
        if payload.signing_mode == "own_device" and not own_account:
            raise AppError("Workers using own-device signing must use their own account.", status_code=403)
        if payload.signing_mode == "supervised_shared_device" and not _can_supervise_flha(db, user):
            raise AppError("A foreperson or manager must supervise shared-device signing.", status_code=403)
    elif user.role not in {"admin", "operations_manager"} and employee.email.lower() != user.email.lower():
        raise AppError("You can only apply your own signature.", status_code=403)
    signatures = list(item.signatures or [])
    if is_flha and any(entry.get("employee_id") == str(employee.id) for entry in signatures):
        raise AppError("This worker has already signed this immutable FLHA version.", status_code=409)
    signatures.append(
        {
            "employee_id": str(employee.id),
            "employee_name": payload.employee_name,
            "acknowledgement": payload.acknowledgement,
            "signed_at": datetime.now(UTC).isoformat(),
            "signed_by_account": user.email,
            "signing_mode": payload.signing_mode,
        }
    )
    item.signatures = signatures
    if is_flha:
        item.details = _audit(item.details or {}, "worker_signed", user, employee_id=str(employee.id), signing_mode=payload.signing_mode)
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def build_alerts(
    vehicles: list[Vehicle],
    records: list[FieldRecord],
    certifications: list[EmployeeCertification],
) -> list[dict]:
    today = date.today()
    alerts: list[dict] = []
    for vehicle in vehicles:
        status = service_status(vehicle)
        if status != "current":
            alerts.append({"type": "vehicle_service", "severity": "high" if status == "overdue" else "medium", "title": f"{vehicle.unit_number} service {status.replace('_', ' ')}", "record_id": str(vehicle.id), "recipients": MANAGEMENT_ALERT_RECIPIENTS})
    for record in records:
        if record.severity in {"medium", "high", "critical"} and record.status not in {"closed", "resolved"}:
            alerts.append({"type": "field_issue", "severity": record.severity, "title": record.title, "record_id": str(record.id), "recipients": record.alert_recipients or MANAGEMENT_ALERT_RECIPIENTS})
    for cert in certifications:
        if cert.expiry_date and cert.expiry_date <= today + timedelta(days=60):
            alerts.append({"type": "ticket_expiry", "severity": "high" if cert.expiry_date < today else "medium", "title": f"{cert.name} {'expired' if cert.expiry_date < today else 'expires soon'}", "record_id": str(cert.id), "recipients": MANAGEMENT_ALERT_RECIPIENTS})
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    return sorted(alerts, key=lambda item: (order.get(item["severity"], 9), item["title"]))


def current_toolbox_talk() -> ToolboxTalk:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return ToolboxTalk(
        week_of=monday,
        title="Health and safety responsibilities on a construction site",
        summary="Confirm who is responsible for identifying, reporting, and controlling hazards before work starts and whenever conditions change.",
        discussion_points=[
            "Supervisors must ensure workers understand the hazards and required controls.",
            "Workers must follow procedures, use required PPE, and report unsafe conditions.",
            "Everyone has the right and responsibility to stop work when a hazard is not controlled.",
            "Record questions, corrective actions, attendance, and every employee acknowledgement.",
        ],
        source_name="WorkSafeBC Toolbox Meeting Guide TG 06-30",
        source_url="https://www.worksafebc.com/resources/health-safety/toolbox-meeting-guides/health-safety-responsibilities-construction?lang=en",
    )


def vehicle_schema(item: Vehicle) -> VehicleRead:
    values = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    return VehicleRead(**values, service_status=service_status(item))


def certification_schema(item: EmployeeCertification) -> CertificationRead:
    today = date.today()
    days = (item.expiry_date - today).days if item.expiry_date else None
    status = "no_expiry" if days is None else "expired" if days < 0 else "expires_soon" if days <= 60 else "current"
    values = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    return CertificationRead(**values, expiry_status=status, days_until_expiry=days)


def service_status(item: Vehicle) -> str:
    today = date.today()
    overdue = (item.next_service_km is not None and item.current_km >= item.next_service_km) or (item.next_service_date is not None and item.next_service_date < today)
    if overdue:
        return "overdue"
    due_soon = (item.next_service_km is not None and item.current_km >= item.next_service_km - 1000) or (item.next_service_date is not None and item.next_service_date <= today + timedelta(days=30))
    return "due_soon" if due_soon else "current"


def require_exists(db: Session, model: type, record_id: UUID, label: str):
    item = db.get(model, record_id)
    if item is None:
        raise AppError(f"{label} not found", status_code=404)
    return item


def commit(db: Session, conflict_message: str = "Unable to save the field record.") -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(conflict_message, status_code=409) from exc
