from datetime import UTC, date, datetime, timedelta
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
from app.models.user import Employee
from app.schemas.field_operations import (
    CertificationCreate,
    CertificationRead,
    EmployeeCreate,
    EmployeeRead,
    FieldOperationsBootstrap,
    FieldRecordCreate,
    FieldRecordRead,
    SignatureCreate,
    TimeEntryCreate,
    TimeEntryRead,
    ToolboxTalk,
    VehicleCreate,
    VehicleLogCreate,
    VehicleLogRead,
    VehicleRead,
    VehicleUpdate,
)
from app.services.auth import AuthenticatedUser
from app.services.cost_codes import get_cost_code_library


MANAGEMENT_ALERT_RECIPIENTS = ["Jeremie Peters", "Mac Warren"]


def get_bootstrap(db: Session) -> FieldOperationsBootstrap:
    employees = list(db.scalars(select(Employee).order_by(Employee.last_name, Employee.first_name)))
    projects = list(db.scalars(select(Project).order_by(Project.name)))
    suppliers = list(db.scalars(select(Supplier).order_by(Supplier.name)))
    equipment = list(db.scalars(select(Equipment).order_by(Equipment.name)))
    vehicles = list(db.scalars(select(Vehicle).order_by(Vehicle.unit_number)))
    vehicle_logs = list(db.scalars(select(VehicleLog).order_by(VehicleLog.entry_date.desc()).limit(100)))
    time_entries = list(db.scalars(select(TimeEntry).order_by(TimeEntry.work_date.desc()).limit(200)))
    records = list(db.scalars(select(FieldRecord).order_by(FieldRecord.work_date.desc(), FieldRecord.created_at.desc()).limit(200)))
    certifications = list(db.scalars(select(EmployeeCertification).order_by(EmployeeCertification.expiry_date)))
    workbooks, production_items = build_job_workbooks(db)
    alerts = build_alerts(vehicles, records, certifications)
    return FieldOperationsBootstrap(
        employees=[EmployeeRead.model_validate(item) for item in employees],
        projects=[{"id": str(item.id), "name": item.name, "project_number": item.project_number, "status": item.status} for item in projects],
        suppliers=[{"id": str(item.id), "name": item.name, "category": item.category} for item in suppliers],
        equipment=[{"id": str(item.id), "name": item.name, "identifier": item.identifier, "status": item.status} for item in equipment],
        cost_codes=[item.model_dump(mode="json") for item in get_cost_code_library().items],
        job_workbooks=workbooks,
        production_items=production_items,
        vehicles=[vehicle_schema(item) for item in vehicles],
        vehicle_logs=[VehicleLogRead.model_validate(item) for item in vehicle_logs],
        time_entries=[TimeEntryRead.model_validate(item) for item in time_entries],
        records=[FieldRecordRead.model_validate(item) for item in records],
        certifications=[certification_schema(item) for item in certifications],
        alerts=alerts,
        toolbox_talk=current_toolbox_talk(),
    )


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


def create_employee(db: Session, payload: EmployeeCreate) -> EmployeeRead:
    item = Employee(**payload.model_dump(), status="active")
    db.add(item)
    commit(db, "An employee with that email already exists.")
    db.refresh(item)
    return EmployeeRead.model_validate(item)


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
    require_exists(db, Employee, payload.employee_id, "Employee")
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
    values["document_ids"] = [str(document_id) for document_id in payload.document_ids]
    values["alert_recipients"] = alerts
    item = FieldRecord(**values, submitted_by=user.email)
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
    if user.role not in {"admin", "operations_manager"} and employee.email.lower() != user.email.lower():
        raise AppError("You can only apply your own signature.", status_code=403)
    signatures = list(item.signatures or [])
    signatures = [entry for entry in signatures if entry.get("employee_id") != str(employee.id)]
    signatures.append(
        {
            "employee_id": str(employee.id),
            "employee_name": payload.employee_name,
            "acknowledgement": payload.acknowledgement,
            "signed_at": datetime.now(UTC).isoformat(),
            "signed_by_account": user.email,
        }
    )
    item.signatures = signatures
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
