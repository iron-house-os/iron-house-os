from datetime import UTC, date, datetime, timedelta
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
    FLHAReassessment,
    FLHARelease,
    FLHAUpdate,
    SafetyRecordUpdate,
    FieldOperationsBootstrap,
    FieldRecordCreate,
    FieldRecordRead,
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
FLHA_SCREENING_ITEMS = [
    "first_aid_equipment",
    "overhead_hazards",
    "underground_utilities_and_locates",
    "mobile_equipment",
    "confined_space",
    "excavation_sloping_shoring_and_access",
    "additional_ppe",
    "traffic_control",
    "subcontractors",
    "basic_ppe_review",
]
FLHA_CONTROL_LEVELS = {"elimination", "substitution", "engineering", "administrative", "ppe"}
FLHA_SERVER_MANAGED_DETAIL_FIELDS = {
    "schema_version",
    "version",
    "root_record_id",
    "previous_record_id",
    "audit_history",
    "release_blockers",
    "supervisor_release",
    "reassessment_reason",
    "changed_conditions",
}
FLHA_PRESETS = [
    {
        "id": "company-excavation",
        "scope": "company",
        "name": "Excavation and utility work",
        "rows": [
            {"task": "Excavate", "hazard": "Underground utility contact", "control": "Confirm current locates, expose services safely and maintain marked limits", "control_level": "engineering", "risk": "critical", "evidence_required": True},
            {"task": "Work near excavation", "hazard": "Cave-in or unsafe access", "control": "Verify sloping or shoring and provide safe access before entry", "control_level": "engineering", "risk": "critical", "evidence_required": True},
        ],
    },
    {
        "id": "company-mobile-equipment",
        "scope": "company",
        "name": "Mobile equipment and ground crew",
        "rows": [
            {"task": "Operate mobile equipment", "hazard": "Worker struck by equipment", "control": "Establish exclusion zone, designated spotter and agreed signals", "control_level": "administrative", "risk": "critical", "evidence_required": False},
        ],
    },
]
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
        records = [
            item for item in records
            if item.employee_id == employee_id
            or item.record_type == "toolbox_talk"
            or (
                item.record_type == "daily_hazard_assessment"
                and str(employee_id) in {
                    str(member.get("id"))
                    for member in (item.details or {}).get("crew") or []
                    if member.get("id")
                }
            )
        ]
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
        flha_presets=[
            *FLHA_PRESETS,
            *[
                {
                    "id": f"project-{item.id}-site-setup",
                    "scope": "project",
                    "project_id": str(item.id),
                    "name": f"{item.name} site setup",
                    "rows": [{
                        "task": "Set up work area",
                        "hazard": "Public or worker enters active work zone",
                        "control": "Verify project access, barriers, signs and communication before work starts",
                        "control_level": "administrative",
                        "risk": "high",
                        "evidence_required": False,
                    }],
                }
                for item in projects
            ],
        ],
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
        if payload.record_type == "daily_hazard_assessment" and profile.portal_role not in {"foreman", "management"}:
            raise AppError("Foreperson access is required to create an FLHA.", status_code=403)
        if profile.portal_role in {"employee", "operator"}:
            if payload.employee_id and payload.employee_id != profile.id:
                raise AppError("You can only create records for your own employee profile.", status_code=403)
            values["employee_id"] = profile.id
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
    if payload.record_type == "daily_hazard_assessment":
        values = prepare_flha_values(values, user, action="created")
    if payload.record_type in {"safety_permit", "corrective_action", "emergency_action_card"}:
        if user.role not in {"admin", "operations_manager"} and (profile is None or profile.portal_role not in {"foreman", "management"}):
            raise AppError("Foreperson or management access is required to create safety-control records.", status_code=403)
        defaults = {"safety_permit": "blocked", "corrective_action": "open", "emergency_action_card": "ready"}
        values["status"] = defaults[payload.record_type]
        values["details"] = {**payload.details, "created_by": user.display_name, "created_at": datetime.now(UTC).isoformat()}
    values["document_ids"] = [str(document_id) for document_id in payload.document_ids]
    values["alert_recipients"] = alerts
    item = FieldRecord(**values, submitted_by=user.email)
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def update_safety_record_status(
    db: Session,
    record_id: UUID,
    payload: SafetyRecordUpdate,
    user: AuthenticatedUser,
) -> FieldRecordRead:
    item = require_exists(db, FieldRecord, record_id, "Safety record")
    if item.record_type not in {"safety_permit", "corrective_action", "emergency_action_card"}:
        raise AppError("That record is not a safety-control record.", status_code=400)
    profile = db.scalar(select(Employee).where(Employee.email.ilike(user.email)))
    if user.role not in {"admin", "operations_manager"} and (profile is None or profile.portal_role not in {"foreman", "management"}):
        raise AppError("Foreperson or management access is required to verify safety-control records.", status_code=403)
    allowed = {
        "safety_permit": {"blocked", "at_risk", "ready"},
        "corrective_action": {"open", "verification", "closed"},
        "emergency_action_card": {"ready"},
    }
    if payload.status not in allowed[item.record_type]:
        raise AppError("That status is not valid for this safety record.", status_code=400)
    history = list((item.details or {}).get("status_history") or [])
    history.append({"from": item.status, "to": payload.status, "by": user.display_name, "at": datetime.now(UTC).isoformat(), "evidence": payload.evidence})
    item.status = payload.status
    item.details = {**(item.details or {}), "verification_evidence": payload.evidence, "status_history": history}
    item.resolved_at = datetime.now(UTC) if payload.status in {"ready", "closed"} else None
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def prepare_flha_values(
    values: dict,
    user: AuthenticatedUser,
    *,
    action: str,
    trusted_details: dict | None = None,
) -> dict:
    now = datetime.now(UTC).isoformat()
    submitted_details = dict(values.get("details") or {})
    details = {
        key: value
        for key, value in submitted_details.items()
        if key not in FLHA_SERVER_MANAGED_DETAIL_FIELDS
    }
    server_details = dict(trusted_details or {})
    details.update({
        key: value
        for key, value in server_details.items()
        if key in FLHA_SERVER_MANAGED_DETAIL_FIELDS
    })
    details["schema_version"] = int(server_details.get("schema_version") or 1)
    details["version"] = int(server_details.get("version") or 1)
    details["root_record_id"] = server_details.get("root_record_id")
    details.setdefault("screening", {})
    details.setdefault("hazards", [])
    details.setdefault("crew", [])
    details.setdefault("emergency", {})
    audit = list(server_details.get("audit_history") or [])
    audit.append({"action": action, "at": now, "by": user.email, "display_name": user.display_name})
    details["audit_history"] = audit
    blockers = flha_release_blockers(values.get("project_id"), values.get("work_date"), details)
    details["release_blockers"] = blockers
    values["details"] = details
    values["signatures"] = []
    values["status"] = "blocked" if critical_flha_blockers(details) else "draft"
    values["severity"] = "critical" if any(str(row.get("risk", "")).lower() == "critical" for row in details["hazards"]) else "high"
    return values


def critical_flha_blockers(details: dict) -> list[str]:
    blockers: list[str] = []
    for index, row in enumerate(details.get("hazards") or [], start=1):
        if str(row.get("risk", "")).lower() != "critical":
            continue
        if not row.get("accepted_control"):
            blockers.append(f"Critical hazard {index} requires an accepted control.")
        if not str(row.get("responsible_person") or "").strip():
            blockers.append(f"Critical hazard {index} requires a responsible person.")
        if row.get("evidence_required") and not str(row.get("evidence") or "").strip():
            blockers.append(f"Critical hazard {index} requires evidence.")
    return blockers


def flha_release_blockers(project_id: object, work_date: object, details: dict) -> list[str]:
    blockers = critical_flha_blockers(details)
    required = {
        "Project / job": project_id,
        "Date": work_date,
        "Site / location": details.get("site_location"),
        "Assessment date and time": details.get("assessment_datetime"),
        "Supervisor / foreperson": (details.get("supervisor") or {}).get("name"),
        "First aid attendant": (details.get("first_aid_attendant") or {}).get("name"),
        "Crew": details.get("crew"),
        "Weather": details.get("weather"),
        "Task, hazard and control rows": details.get("hazards"),
    }
    blockers.extend(f"{label} is required." for label, value in required.items() if not value)
    screening = details.get("screening") or {}
    for item in FLHA_SCREENING_ITEMS:
        if screening.get(item) not in {"yes", "no", "na"}:
            blockers.append(f"Screening response is required for {item.replace('_', ' ')}.")
    for index, row in enumerate(details.get("hazards") or [], start=1):
        if not all(str(row.get(key) or "").strip() for key in ("task", "hazard", "control", "responsible_person")):
            blockers.append(f"Hazard row {index} requires task, hazard, control and responsible person.")
        if row.get("control_level") not in FLHA_CONTROL_LEVELS:
            blockers.append(f"Hazard row {index} requires a hierarchy-of-controls category.")
    emergency = details.get("emergency") or {}
    for key in ("response_plan", "muster_point", "first_aid_location", "communication", "stop_work_triggers"):
        if not str(emergency.get(key) or "").strip():
            blockers.append(f"Emergency {key.replace('_', ' ')} is required.")
    return list(dict.fromkeys(blockers))


def _flha_profile(db: Session, user: AuthenticatedUser) -> Employee | None:
    return db.scalar(select(Employee).where(Employee.email.ilike(user.email)))


def _can_supervise_flha(db: Session, user: AuthenticatedUser) -> bool:
    profile = _flha_profile(db, user)
    return user.role in {"admin", "operations_manager"} or bool(profile and profile.portal_role in {"foreman", "management"})


def _require_flha(item: FieldRecord) -> None:
    if item.record_type != "daily_hazard_assessment":
        raise AppError("That record is not an FLHA.", status_code=400)


def update_flha(db: Session, record_id: UUID, payload: FLHAUpdate, user: AuthenticatedUser) -> FieldRecordRead:
    item = require_exists(db, FieldRecord, record_id, "FLHA")
    _require_flha(item)
    if item.signatures or item.status == "released":
        raise AppError("Signed FLHAs are immutable. Create a re-assessment instead.", status_code=409)
    if item.submitted_by != user.email and not _can_supervise_flha(db, user):
        raise AppError("You do not have permission to edit this FLHA.", status_code=403)
    if payload.project_id:
        require_exists(db, Project, payload.project_id, "Project")
    values = prepare_flha_values(
        {
            "project_id": payload.project_id,
            "work_date": payload.work_date,
            "title": payload.title,
            "details": payload.details,
            "document_ids": [str(value) for value in payload.document_ids],
        },
        user,
        action="edited",
        trusted_details={
            key: value
            for key, value in (item.details or {}).items()
            if key in FLHA_SERVER_MANAGED_DETAIL_FIELDS and key != "release_blockers"
        },
    )
    for key in ("project_id", "work_date", "title", "details", "document_ids", "status", "severity"):
        setattr(item, key, values[key])
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def reassess_flha(db: Session, record_id: UUID, payload: FLHAReassessment, user: AuthenticatedUser) -> FieldRecordRead:
    previous = require_exists(db, FieldRecord, record_id, "FLHA")
    _require_flha(previous)
    if not _can_supervise_flha(db, user):
        raise AppError("Foreperson access is required to re-assess an FLHA.", status_code=403)
    if payload.project_id:
        require_exists(db, Project, payload.project_id, "Project")
    previous_details = dict(previous.details or {})
    version = int(previous_details.get("version") or 1) + 1
    root_id = previous_details.get("root_record_id") or str(previous.id)
    trusted_details = {
        "schema_version": int(previous_details.get("schema_version") or 1),
        "version": version,
        "root_record_id": root_id,
        "previous_record_id": str(previous.id),
        "reassessment_reason": payload.reason,
        "changed_conditions": payload.changed_conditions,
        "audit_history": list(previous_details.get("audit_history") or []),
    }
    values = prepare_flha_values(
        {
            "record_type": "daily_hazard_assessment",
            "project_id": payload.project_id,
            "employee_id": previous.employee_id,
            "work_date": payload.work_date,
            "title": payload.title,
            "details": payload.details,
            "document_ids": [str(value) for value in payload.document_ids],
        },
        user,
        action="reassessed",
        trusted_details=trusted_details,
    )
    values["details"]["audit_history"][-1].update({"reason": payload.reason, "changed_conditions": payload.changed_conditions, "previous_record_id": str(previous.id)})
    item = FieldRecord(**values, alert_recipients=previous.alert_recipients or [], submitted_by=user.email)
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def release_flha(db: Session, record_id: UUID, payload: FLHARelease, user: AuthenticatedUser) -> FieldRecordRead:
    item = require_exists(db, FieldRecord, record_id, "FLHA")
    _require_flha(item)
    if item.status == "released":
        raise AppError("This FLHA has already been released.", status_code=409)
    if not _can_supervise_flha(db, user):
        raise AppError("Foreperson access is required to release an FLHA.", status_code=403)
    details = dict(item.details or {})
    blockers = flha_release_blockers(item.project_id, item.work_date, details)
    crew_ids = {str(member.get("id")) for member in details.get("crew") or [] if member.get("id")}
    signed_ids = {str(signature.get("employee_id")) for signature in item.signatures or []}
    missing_signatures = crew_ids - signed_ids
    if missing_signatures:
        blockers.append(f"{len(missing_signatures)} crew acknowledgement(s) are still required.")
    if blockers:
        raise AppError("FLHA release blocked: " + " ".join(blockers), status_code=409)
    now = datetime.now(UTC).isoformat()
    details["release_blockers"] = []
    details["supervisor_release"] = {"released_at": now, "released_by": user.email, "display_name": user.display_name, "verification": payload.verification}
    audit = list(details.get("audit_history") or [])
    audit.append({"action": "supervisor_released", "at": now, "by": user.email, "display_name": user.display_name})
    details["audit_history"] = audit
    item.details = details
    item.status = "released"
    item.resolved_at = datetime.now(UTC)
    db.add(item)
    commit(db)
    db.refresh(item)
    return FieldRecordRead.model_validate(item)


def get_flha_for_user(db: Session, record_id: UUID, user: AuthenticatedUser) -> FieldRecord:
    item = require_exists(db, FieldRecord, record_id, "FLHA")
    _require_flha(item)
    if user.role != "viewer":
        return item
    profile = _flha_profile(db, user)
    crew_ids = {str(member.get("id")) for member in (item.details or {}).get("crew") or [] if member.get("id")}
    if not profile or (str(profile.id) not in crew_ids and profile.portal_role not in {"foreman", "management"}):
        raise AppError("You do not have permission to view this FLHA.", status_code=403)
    return item


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
    own_signature = employee.email.lower() == user.email.lower()
    supervised_signature = payload.supervised_shared_device and _can_supervise_flha(db, user)
    if item.record_type == "daily_hazard_assessment":
        if not own_signature and not supervised_signature:
            raise AppError("Workers must sign on their own account or in a supervised shared-device flow.", status_code=403)
        if supervised_signature and not payload.worker_confirmation:
            raise AppError("Shared-device signatures require the worker's explicit confirmation.", status_code=400)
        if supervised_signature and not str(payload.supervisor_confirmation or "").strip():
            raise AppError("Shared-device signatures require supervisor confirmation.", status_code=400)
    elif user.role not in {"admin", "operations_manager"} and not own_signature:
        raise AppError("You can only apply your own signature.", status_code=403)
    signatures = list(item.signatures or [])
    if any(entry.get("employee_id") == str(employee.id) for entry in signatures):
        raise AppError("This worker has already acknowledged this version.", status_code=409)
    if item.record_type == "daily_hazard_assessment":
        details = dict(item.details or {})
        blockers = flha_release_blockers(item.project_id, item.work_date, details)
        if blockers:
            raise AppError("FLHA acknowledgement blocked until required fields and controls are complete: " + " ".join(blockers), status_code=409)
        crew_ids = {str(member.get("id")) for member in details.get("crew") or [] if member.get("id")}
        if str(employee.id) not in crew_ids:
            raise AppError("Only workers listed on this FLHA may acknowledge it.", status_code=403)
    employee_name = f"{employee.first_name} {employee.last_name}"
    signatures.append(
        {
            "employee_id": str(employee.id),
            "employee_name": employee_name,
            "acknowledgement": payload.acknowledgement,
            "signed_at": datetime.now(UTC).isoformat(),
            "signed_by_account": user.email,
            "signing_method": "supervised_shared_device" if supervised_signature else "own_device",
            "worker_confirmation": payload.worker_confirmation if supervised_signature else True,
            "supervisor_confirmation": payload.supervisor_confirmation if supervised_signature else None,
        }
    )
    item.signatures = signatures
    if item.record_type == "daily_hazard_assessment":
        details = dict(item.details or {})
        audit = list(details.get("audit_history") or [])
        audit.append({
            "action": "worker_acknowledged",
            "at": signatures[-1]["signed_at"],
            "by": user.email,
            "employee_id": str(employee.id),
            "employee_name": employee_name,
            "signing_method": signatures[-1]["signing_method"],
        })
        details["audit_history"] = audit
        item.details = details
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
