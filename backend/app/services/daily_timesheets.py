"""Controlled Foreman daily time sheet workflow."""

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.bid import Bid
from app.models.equipment import Equipment
from app.models.field_operations import FieldRecord, TimeEntry
from app.models.finance import Receipt
from app.models.project import Project
from app.models.supplier import Supplier
from app.models.user import Employee
from app.schemas.daily_timesheet import DailyTimesheetAction, DailyTimesheetBootstrap, DailyTimesheetRead, DailyTimesheetRevision, DailyTimesheetWrite
from app.services.auth import AuthenticatedUser
from app.services.field_operations import commit


MANAGEMENT_ROLES = {"admin", "operations_manager"}


def _profile(db: Session, user: AuthenticatedUser) -> Employee | None:
    return db.scalar(select(Employee).where(Employee.email.ilike(user.email)))


def _require_foreman(db: Session, user: AuthenticatedUser) -> None:
    profile = _profile(db, user)
    if user.role not in MANAGEMENT_ROLES and not (profile and profile.portal_role in {"foreman", "management"}):
        raise AppError("Foreman or authorized project/office access is required.", status_code=403)


def _require_management(user: AuthenticatedUser) -> None:
    if user.role not in MANAGEMENT_ROLES:
        raise AppError("Authorized project/office approval access is required.", status_code=403)


def _event(action: str, user: AuthenticatedUser, *, reason: str | None = None, from_status: str | None = None, to_status: str | None = None) -> dict:
    return {"action": action, "actor": user.email, "display_name": user.display_name, "at": datetime.now(UTC).isoformat(), "reason": reason, "from_status": from_status, "to_status": to_status}


def _project_cost_codes(db: Session) -> dict[str, list[dict]]:
    bids = list(db.scalars(select(Bid).order_by(Bid.project_id, Bid.created_at.desc())))
    result: dict[str, list[dict]] = {}
    seen: set[UUID] = set()
    for bid in bids:
        if bid.project_id in seen or (bid.bid_json or {}).get("source") != "estimate_workspace":
            continue
        seen.add(bid.project_id)
        lines = ((bid.bid_json or {}).get("estimate") or {}).get("line_items") or []
        codes: dict[str, dict] = {}
        for line in lines:
            code = str(line.get("code") or "").strip().upper()
            if code:
                codes[code] = {"code": code, "name": str(line.get("description") or code)}
        result[str(bid.project_id)] = list(codes.values())
    return result


def _assigned_crew(db: Session) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    records = db.scalars(select(FieldRecord).where(FieldRecord.record_type == "crew_shift"))
    for record in records:
        if record.project_id and record.employee_id and record.status not in {"cancelled", "void", "inactive"}:
            employee_id = str(record.employee_id)
            if employee_id not in result[str(record.project_id)]:
                result[str(record.project_id)].append(employee_id)
    return dict(result)


def _records(db: Session) -> list[FieldRecord]:
    return list(db.scalars(select(FieldRecord).where(FieldRecord.record_type == "daily_timesheet").order_by(FieldRecord.work_date.desc(), FieldRecord.created_at.desc())))


def bootstrap(db: Session, user: AuthenticatedUser) -> DailyTimesheetBootstrap:
    _require_foreman(db, user)
    projects = list(db.scalars(select(Project).order_by(Project.project_number, Project.name)))
    employees = list(db.scalars(select(Employee).where(Employee.status == "active").order_by(Employee.last_name, Employee.first_name)))
    equipment = list(db.scalars(select(Equipment).where(Equipment.status.in_(["active", "available"])).order_by(Equipment.name)))
    vendors = list(db.scalars(select(Supplier).order_by(Supplier.name)))
    rentals = list(db.scalars(select(FieldRecord).where(FieldRecord.record_type == "rental_equipment", FieldRecord.status.not_in(["inactive", "void", "closed"])).order_by(FieldRecord.work_date.desc())))
    receipts = list(db.scalars(select(Receipt).where(Receipt.status != "void").order_by(Receipt.receipt_date.desc()).limit(100)))
    return DailyTimesheetBootstrap(
        projects=[{"id": str(item.id), "name": item.name, "project_number": item.project_number or "Unnumbered", "status": item.status} for item in projects if item.status not in {"closed", "cancelled", "inactive"}],
        employees=[{"id": str(item.id), "code": "EMP-" + str(item.id)[:6].upper(), "name": f"{item.first_name} {item.last_name}", "classification": item.role or item.portal_role.replace("_", " ").title(), "portal_role": item.portal_role} for item in employees],
        equipment=[{"id": str(item.id), "name": item.name, "identifier": item.identifier, "status": item.status} for item in equipment],
        rentals=[{"id": str(item.id), "name": item.title, "project_id": str(item.project_id) if item.project_id else None, "vendor_id": str(item.supplier_id) if item.supplier_id else None, "status": item.status} for item in rentals],
        vendors=[{"id": str(item.id), "name": item.name, "category": item.category} for item in vendors],
        receipts=[{"id": str(item.id), "reference": item.reference, "vendor_name": item.vendor_name, "receipt_date": item.receipt_date, "status": item.status} for item in receipts],
        project_cost_codes=_project_cost_codes(db), assigned_crew=_assigned_crew(db), sheets=[_read(item) for item in _records(db)], can_approve=user.role in MANAGEMENT_ROLES,
    )


def _active(db: Session, model: type, item_id: UUID, label: str, allowed_status: set[str] | None = None):
    item = db.get(model, item_id)
    if item is None:
        raise AppError(f"{label} is not an active system record.", status_code=400)
    status_value = str(getattr(item, "status", "active")).lower()
    if allowed_status is not None and status_value not in allowed_status:
        raise AppError(f"{label} is inactive or unavailable.", status_code=400)
    if allowed_status is None and status_value in {"inactive", "void", "closed", "cancelled"}:
        raise AppError(f"{label} is inactive or unavailable.", status_code=400)
    return item


def _validated_details(db: Session, payload: DailyTimesheetWrite) -> dict:
    project = _active(db, Project, payload.project_id, "Job")
    supervisor = _active(db, Employee, payload.supervisor_id, "Supervisor", {"active"})
    manager = _active(db, Employee, payload.project_manager_id, "Project manager", {"active"}) if payload.project_manager_id else None
    allowed = {item["code"] for item in _project_cost_codes(db).get(str(payload.project_id), [])}
    if not allowed:
        raise AppError("The selected job has no approved estimate cost codes.", status_code=400)

    def check_code(code: str) -> str:
        normalized = code.strip().upper()
        if normalized not in allowed:
            raise AppError(f"Cost code {normalized} is not approved for the selected job.", status_code=400)
        return normalized

    labour = []
    for line in payload.labour:
        employee = _active(db, Employee, line.employee_id, "Employee", {"active"})
        operator_equipment = _active(db, Equipment, line.equipment_id, "Operator equipment", {"active", "available"}) if line.equipment_id else None
        labour.append({"employee_id": str(employee.id), "employee_code": "EMP-" + str(employee.id)[:6].upper(), "employee_name": f"{employee.first_name} {employee.last_name}", "classification": employee.role or employee.portal_role.replace("_", " ").title(), "equipment_id": str(operator_equipment.id) if operator_equipment else None, "splits": [{**item.model_dump(), "cost_code": check_code(item.cost_code)} for item in line.splits]})
    equipment_lines = []
    for line in payload.equipment:
        if line.source == "owned":
            resource = _active(db, Equipment, line.resource_id, "Equipment", {"active", "available"})
            resource_name = resource.name
        else:
            resource = _active(db, FieldRecord, line.resource_id, "Rental equipment")
            if resource.record_type != "rental_equipment" or resource.project_id not in {None, payload.project_id}:
                raise AppError("Rental equipment is not active for the selected job.", status_code=400)
            resource_name = resource.title
        vendor = _active(db, Supplier, line.vendor_id, "Vendor") if line.vendor_id else None
        equipment_lines.append({**line.model_dump(mode="json"), "resource_name": resource_name, "vendor_name": vendor.name if vendor else None, "splits": [{**split.model_dump(), "cost_code": check_code(split.cost_code)} for split in line.splits]})
    materials = []
    for line in payload.materials:
        vendor = _active(db, Supplier, line.vendor_id, "Vendor")
        if line.receipt_id:
            _active(db, Receipt, line.receipt_id, "Receipt")
        materials.append({**line.model_dump(mode="json"), "vendor_name": vendor.name, "cost_code": check_code(line.cost_code)})
    code_totals: dict[str, dict[str, float]] = defaultdict(lambda: {"straight_time": 0, "overtime": 0, "equipment_quantity": 0, "material_quantity": 0, "production_quantity": 0})
    employee_totals: dict[str, dict[str, float]] = {}
    for line in labour:
        straight = sum(float(item["straight_time"]) for item in line["splits"])
        overtime = sum(float(item["overtime"]) for item in line["splits"])
        employee_totals[line["employee_id"]] = {"straight_time": straight, "overtime": overtime, "total": straight + overtime}
        for split in line["splits"]:
            code_totals[split["cost_code"]]["straight_time"] += float(split["straight_time"])
            code_totals[split["cost_code"]]["overtime"] += float(split["overtime"])
    for line in equipment_lines:
        for split in line["splits"]:
            code_totals[split["cost_code"]]["equipment_quantity"] += float(split["quantity"])
    for line in materials:
        code_totals[line["cost_code"]]["material_quantity"] += float(line["quantity"])
        code_totals[line["cost_code"]]["production_quantity"] += float(line["production_quantity"] or 0)
    sheet_straight = sum(item["straight_time"] for item in employee_totals.values())
    sheet_overtime = sum(item["overtime"] for item in employee_totals.values())
    return {"schema_version": 1, "shift": payload.shift, "project_name": project.name, "project_number": project.project_number, "project_manager_id": str(manager.id) if manager else None, "project_manager_name": f"{manager.first_name} {manager.last_name}" if manager else None, "supervisor_id": str(supervisor.id), "supervisor_name": f"{supervisor.first_name} {supervisor.last_name}", "weather": payload.weather, "site_conditions": payload.site_conditions, "labour": labour, "equipment": equipment_lines, "materials": materials, "narrative": payload.narrative.model_dump(), "employee_totals": employee_totals, "cost_code_totals": dict(code_totals), "sheet_totals": {"straight_time": sheet_straight, "overtime": sheet_overtime, "labour_hours": sheet_straight + sheet_overtime}}


def _read(record: FieldRecord) -> DailyTimesheetRead:
    details = record.details or {}
    return DailyTimesheetRead(id=record.id, status=record.status, version=int(details.get("version", 1)), project_id=record.project_id, work_date=record.work_date, shift=details.get("shift", "day"), details=details, document_ids=[UUID(str(value)) for value in record.document_ids or []], submitted_by=record.submitted_by, created_at=record.created_at, updated_at=record.updated_at)


def _get(db: Session, sheet_id: UUID) -> FieldRecord:
    record = db.get(FieldRecord, sheet_id)
    if record is None or record.record_type != "daily_timesheet":
        raise AppError("Daily time sheet not found.", status_code=404)
    return record


def save_draft(db: Session, payload: DailyTimesheetWrite, user: AuthenticatedUser, sheet_id: UUID | None = None) -> DailyTimesheetRead:
    _require_foreman(db, user)
    details = _validated_details(db, payload)
    document_ids = [str(item) for item in payload.document_ids]
    if sheet_id:
        record = _get(db, sheet_id)
        if record.status != "draft":
            raise AppError("Submitted daily sheets are immutable. Create a revision with a reason.", status_code=409)
        old = record.details or {}
        audit = [*(old.get("audit_history") or []), _event("draft_autosaved", user, from_status="draft", to_status="draft")]
        record.project_id, record.work_date, record.title = payload.project_id, payload.work_date, f"{details['project_number'] or details['project_name']} — Foreman Daily Time Sheet"
        record.details = {**details, "version": int(old.get("version", 1)), "root_record_id": old.get("root_record_id"), "previous_record_id": old.get("previous_record_id"), "audit_history": audit}
        record.document_ids = document_ids
    else:
        record = FieldRecord(record_type="daily_timesheet", project_id=payload.project_id, work_date=payload.work_date, title=f"{details['project_number'] or details['project_name']} — Foreman Daily Time Sheet", status="draft", severity="medium" if payload.narrative.potential_change else "none", details={**details, "version": 1, "root_record_id": None, "previous_record_id": None, "audit_history": [_event("draft_created", user, to_status="draft")]}, document_ids=document_ids, signatures=[], alert_recipients=[], submitted_by=user.email)
        db.add(record)
    record.severity = "medium" if payload.narrative.potential_change else "none"
    commit(db)
    db.refresh(record)
    if record.details.get("root_record_id") is None:
        record.details = {**record.details, "root_record_id": str(record.id)}
        commit(db)
        db.refresh(record)
    return _read(record)


def submit(db: Session, sheet_id: UUID, user: AuthenticatedUser) -> DailyTimesheetRead:
    _require_foreman(db, user)
    record = _get(db, sheet_id)
    if record.status != "draft":
        raise AppError("Only a draft daily sheet can be submitted.", status_code=409)
    details = record.details or {}
    if not details.get("labour"):
        raise AppError("Add at least one crew labour entry before submitting.", status_code=400)
    audit = [*(details.get("audit_history") or []), _event("submitted_by_foreman", user, from_status="draft", to_status="submitted"), _event("queued_for_review", user, from_status="submitted", to_status="needs_review")]
    record.status = "needs_review"
    record.details = {**details, "submitted_at": datetime.now(UTC).isoformat(), "audit_history": audit, "review_item": {"type": "potential_change", "status": "open"} if (details.get("narrative") or {}).get("potential_change") else None}
    commit(db)
    db.refresh(record)
    return _read(record)


def decide(db: Session, sheet_id: UUID, action: str, payload: DailyTimesheetAction, user: AuthenticatedUser) -> DailyTimesheetRead:
    _require_management(user)
    record = _get(db, sheet_id)
    transitions = {"approve": ({"needs_review"}, "approved"), "reject": ({"needs_review"}, "rejected"), "void": ({"draft", "needs_review", "approved", "rejected"}, "void"), "reopen": ({"rejected", "approved"}, "draft")}
    allowed, target = transitions[action]
    if record.status not in allowed:
        raise AppError(f"A {record.status} daily sheet cannot be {action}d.", status_code=409)
    if action in {"reject", "void", "reopen"} and not (payload.reason or "").strip():
        raise AppError(f"A reason is required to {action} a daily sheet.", status_code=400)
    previous = record.status
    record.status = target
    record.details = {**(record.details or {}), "audit_history": [*((record.details or {}).get("audit_history") or []), _event(action + "d", user, reason=payload.reason, from_status=previous, to_status=target)]}
    commit(db)
    db.refresh(record)
    return _read(record)


def create_revision(db: Session, sheet_id: UUID, payload: DailyTimesheetRevision, user: AuthenticatedUser) -> DailyTimesheetRead:
    _require_foreman(db, user)
    source = _get(db, sheet_id)
    if source.status == "draft":
        raise AppError("Edit the existing draft instead of creating a revision.", status_code=409)
    details = dict(source.details or {})
    details.update({"version": int(details.get("version", 1)) + 1, "previous_record_id": str(source.id), "revision_reason": payload.reason, "audit_history": [*(details.get("audit_history") or []), _event("revision_created", user, reason=payload.reason, from_status=source.status, to_status="draft")]})
    revision = FieldRecord(record_type="daily_timesheet", project_id=source.project_id, work_date=source.work_date, title=source.title, status="draft", severity=source.severity, details=details, document_ids=list(source.document_ids or []), signatures=[], alert_recipients=[], submitted_by=user.email)
    db.add(revision)
    commit(db)
    db.refresh(revision)
    return _read(revision)


def export_csv(db: Session, sheet_id: UUID, user: AuthenticatedUser) -> tuple[str, str]:
    _require_management(user)
    record = _get(db, sheet_id)
    if record.status not in {"approved", "exported"}:
        raise AppError("Only approved daily sheets can be exported.", status_code=409)
    details = record.details or {}
    rows = ["employee_code,employee_name,classification,cost_code,straight_time,overtime"]
    for line in details.get("labour") or []:
        for split in line.get("splits") or []:
            values = [line.get("employee_code"), line.get("employee_name"), line.get("classification"), split.get("cost_code"), split.get("straight_time"), split.get("overtime")]
            rows.append(",".join('"' + str(value or '').replace('"', '""') + '"' for value in values))
    if record.status == "approved":
        record.status = "exported"
        record.details = {**details, "audit_history": [*(details.get("audit_history") or []), _event("exported", user, from_status="approved", to_status="exported")]}
        commit(db)
    return f"daily-timesheet-{record.work_date}-v{details.get('version', 1)}.csv", "\n".join(rows) + "\n"


def post_time_entries(db: Session, sheet_id: UUID, user: AuthenticatedUser) -> DailyTimesheetRead:
    _require_management(user)
    record = _get(db, sheet_id)
    if record.status not in {"approved", "exported"}:
        raise AppError("Only approved daily sheets can be posted.", status_code=409)
    details = record.details or {}
    if details.get("posted_at"):
        raise AppError("This daily sheet has already been posted.", status_code=409)
    for line in details.get("labour") or []:
        for split in line.get("splits") or []:
            db.add(TimeEntry(employee_id=UUID(line["employee_id"]), project_id=record.project_id, cost_code=split["cost_code"], work_date=record.work_date, regular_hours=split["straight_time"], overtime_hours=split["overtime"], entry_type="foreman_crew", notes=f"Daily sheet {record.id} v{details.get('version', 1)}", status="approved", submitted_by=record.submitted_by))
    record.details = {**details, "posted_at": datetime.now(UTC).isoformat(), "posted_by": user.email, "audit_history": [*(details.get("audit_history") or []), _event("posted", user, from_status=record.status, to_status=record.status)]}
    commit(db)
    db.refresh(record)
    return _read(record)


def get_for_pdf(db: Session, sheet_id: UUID, user: AuthenticatedUser) -> FieldRecord:
    _require_management(user)
    record = _get(db, sheet_id)
    if record.status not in {"approved", "exported"}:
        raise AppError("Only approved daily sheets can be exported.", status_code=409)
    return record
