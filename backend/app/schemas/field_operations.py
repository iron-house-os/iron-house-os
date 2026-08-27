from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PortalRole = Literal["employee", "operator", "foreman", "management"]
Severity = Literal["none", "low", "medium", "high", "critical"]
RecordType = Literal[
    "journal",
    "expense",
    "missing_form",
    "job_photo",
    "equipment_inspection",
    "daily_hazard_assessment",
    "toolbox_talk",
    "time_off_request",
    "crew_shift",
    "performance_review",
    "material_quantity",
    "material_movement",
    "milestone_review",
    "small_equipment_inspection",
    "subcontractor",
    "rental_equipment",
    "weather",
    "daily_timesheet",
    "purchase_order_request",
    "safety_permit",
    "corrective_action",
    "emergency_action_card",
    "incident",
    "first_aid_record",
    "completed_work",
]


MONEY = Decimal("0.01")


class EmployeeCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    role: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=500)
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=80)
    emergency_contact_relationship: str | None = Field(default=None, max_length=120)
    hire_date: date | None = None
    portal_role: PortalRole = "employee"
    notes: str | None = None
    provision_portal_access: bool = Field(default=True, exclude=True)
    temporary_password: str | None = Field(default=None, min_length=12, max_length=512, exclude=True)


class EmployeeRead(EmployeeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    portal_access_created: bool = False
    temporary_password: str | None = None


class CertificationCreate(BaseModel):
    employee_id: UUID
    name: str = Field(min_length=1, max_length=255)
    issuer: str | None = Field(default=None, max_length=255)
    certificate_number: str | None = Field(default=None, max_length=120)
    issued_date: date | None = None
    expiry_date: date | None = None
    document_id: UUID | None = None
    notes: str | None = None


class CertificationRead(CertificationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    expiry_status: Literal["current", "expires_soon", "expired", "no_expiry"]
    days_until_expiry: int | None
    created_at: datetime
    updated_at: datetime


class VehicleCreate(BaseModel):
    unit_number: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=255)
    assigned_driver_name: str | None = Field(default=None, max_length=255)
    assigned_employee_id: UUID | None = None
    make: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1900, le=2200)
    vin: str | None = Field(default=None, max_length=40)
    licence_plate: str | None = Field(default=None, max_length=40)
    current_km: float = Field(default=0, ge=0)
    next_service_km: float | None = Field(default=None, ge=0)
    next_service_date: date | None = None
    status: str = Field(default="active", max_length=40)
    notes: str | None = None


class VehicleUpdate(BaseModel):
    assigned_driver_name: str | None = Field(default=None, max_length=255)
    assigned_employee_id: UUID | None = None
    licence_plate: str | None = Field(default=None, max_length=40)
    current_km: float | None = Field(default=None, ge=0)
    next_service_km: float | None = Field(default=None, ge=0)
    next_service_date: date | None = None
    status: str | None = Field(default=None, max_length=40)
    notes: str | None = None


class VehicleRead(VehicleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_status: Literal["current", "due_soon", "overdue"]
    created_at: datetime
    updated_at: datetime


class VehicleLogCreate(BaseModel):
    vehicle_id: UUID
    employee_id: UUID | None = None
    project_id: UUID | None = None
    log_type: Literal["fuel", "mileage", "maintenance", "inspection", "repair"]
    entry_date: date
    odometer_km: float | None = Field(default=None, ge=0)
    litres: float | None = Field(default=None, ge=0)
    amount: float | None = Field(default=None, ge=0)
    vendor: str | None = Field(default=None, max_length=255)
    details: str | None = None
    document_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_useful_value(self) -> "VehicleLogCreate":
        if self.odometer_km is None and self.litres is None and self.amount is None and not self.details:
            raise ValueError("Enter kilometres, fuel, cost, or details.")
        return self


class VehicleLogRead(VehicleLogCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class TimeEntryCreate(BaseModel):
    employee_id: UUID
    project_id: UUID
    cost_code: str = Field(min_length=3, max_length=32)
    work_date: date
    regular_hours: float = Field(default=0, ge=0, le=24)
    overtime_hours: float = Field(default=0, ge=0, le=24)
    entry_type: Literal["employee", "foreman_crew", "operator"] = "employee"
    notes: str | None = None

    @model_validator(mode="after")
    def validate_hours(self) -> "TimeEntryCreate":
        if self.regular_hours + self.overtime_hours <= 0:
            raise ValueError("At least one hour is required.")
        if self.regular_hours + self.overtime_hours > 24:
            raise ValueError("Total hours cannot exceed 24.")
        return self


class TimeEntryRead(TimeEntryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    submitted_by: str | None
    created_at: datetime
    updated_at: datetime


class FieldRecordCreate(BaseModel):
    record_type: RecordType
    project_id: UUID | None = None
    employee_id: UUID | None = None
    equipment_id: UUID | None = None
    supplier_id: UUID | None = None
    cost_code: str | None = Field(default=None, max_length=32)
    work_date: date
    title: str = Field(min_length=1, max_length=255)
    status: str = Field(default="submitted", max_length=40)
    severity: Severity = "none"
    details: dict = Field(default_factory=dict)
    document_ids: list[UUID] = Field(default_factory=list)
    signatures: list[dict] = Field(default_factory=list)
    alert_recipients: list[str] = Field(default_factory=list)

    @field_validator("alert_recipients")
    @classmethod
    def default_management_alerts(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @model_validator(mode="after")
    def validate_material_movement(self) -> "FieldRecordCreate":
        if self.record_type == "material_movement":
            direction = self.details.get("direction")
            material_type = str(self.details.get("material_type") or "").strip()
            try:
                loads = float(self.details.get("loads") or 0)
                total_tonnes = float(self.details.get("total_tonnes") or 0)
            except (TypeError, ValueError) as exc:
                raise ValueError("Loads and total tonnes must be numbers.") from exc
            if direction not in {"imported", "exported"}:
                raise ValueError("Material direction must be imported or exported.")
            if not material_type:
                raise ValueError("Select a material type.")
            if loads <= 0 or total_tonnes <= 0:
                raise ValueError("Loads and total tonnes must be greater than zero.")
        if self.record_type == "crew_shift":
            if not self.employee_id or not self.project_id:
                raise ValueError("Crew shifts require an employee and project.")
            if not self.details.get("start_time") or not self.details.get("end_time"):
                raise ValueError("Crew shifts require start and end times.")
        if self.record_type == "time_off_request":
            try:
                start = date.fromisoformat(str(self.details.get("start_date") or ""))
                end = date.fromisoformat(str(self.details.get("end_date") or ""))
            except ValueError as exc:
                raise ValueError("Time-off requests require valid start and end dates.") from exc
            if end < start:
                raise ValueError("Time-off end date cannot be before the start date.")
        if self.record_type == "incident":
            if self.details.get("occurrence_kind") not in {"incident", "near_miss"}:
                raise ValueError("Select incident or near miss.")
            required = {
                "occurred_at": "Enter when the occurrence happened.",
                "location": "Enter the occurrence location.",
                "description": "Describe what happened.",
                "immediate_controls": "Record the immediate controls taken.",
            }
            for key, message in required.items():
                if not str(self.details.get(key) or "").strip():
                    raise ValueError(message)
            try:
                occurred_at = datetime.fromisoformat(str(self.details["occurred_at"]).replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("Enter a valid occurrence date and time.") from exc
            self.work_date = occurred_at.date()
        if self.record_type == "first_aid_record":
            if not self.employee_id:
                raise ValueError("Select the worker for the first-aid occurrence.")
            required = {
                "occurred_at": "Enter when the occurrence happened.",
                "location": "Enter the occurrence location.",
                "first_aid_attendant": "Enter the first-aid attendant.",
                "general_nature": "Enter the general nature of the occurrence.",
                "aid_provided": "Record the aid provided.",
            }
            for key, message in required.items():
                if not str(self.details.get(key) or "").strip():
                    raise ValueError(message)
            if self.details.get("outcome") not in {
                "returned_to_work",
                "referred_for_further_assessment",
                "transported_for_further_assessment",
            }:
                raise ValueError("Select the recorded outcome.")
        if self.record_type == "completed_work":
            if not self.project_id:
                raise ValueError("Completed work requires a project.")
            if self.severity != "none" or self.alert_recipients:
                raise ValueError("Completed-work revenue records cannot carry safety severity or alerts.")
            required = {
                "source_import_key": "Completed work requires a source import key.",
                "source_line_key": "Completed work requires a source line key.",
                "source_invoice_number": "Completed work requires a source invoice number.",
                "source_drive_file_id": "Completed work requires a source Drive file ID.",
                "source_invoice_date": "Completed work requires a source invoice date.",
                "description": "Completed work requires a description.",
                "unit": "Completed work requires a unit.",
            }
            for key, message in required.items():
                if not str(self.details.get(key) or "").strip():
                    raise ValueError(message)
            if self.details.get("cost_status") != "internal_cost_unverified":
                raise ValueError("Completed work must identify internal cost as unverified.")
            if self.details.get("revenue_trace_only") is not True:
                raise ValueError("Completed work must be marked as revenue trace only.")
            prohibited_cost_fields = {
                "actual_cost",
                "actual_cost_amount",
                "internal_cost_amount",
                "internal_cost_rate",
            }
            if prohibited_cost_fields.intersection(self.details):
                raise ValueError("Unverified completed work cannot include internal actual-cost values.")
            try:
                quantity = Decimal(str(self.details.get("quantity")))
                billable_rate = Decimal(str(self.details.get("billable_rate")))
                billable_amount = Decimal(str(self.details.get("billable_amount")))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("Completed-work quantity, billable rate, and billable amount must be numbers.") from exc
            if not all(value.is_finite() for value in (quantity, billable_rate, billable_amount)):
                raise ValueError("Completed-work quantity, billable rate, and billable amount must be finite.")
            if quantity <= 0 or billable_rate <= 0 or billable_amount <= 0:
                raise ValueError("Completed-work quantity, billable rate, and billable amount must be greater than zero.")
            if billable_rate != billable_rate.quantize(MONEY) or billable_amount != billable_amount.quantize(MONEY):
                raise ValueError("Completed-work billable rate and amount must use two-decimal currency precision.")
            expected_amount = (quantity * billable_rate).quantize(MONEY, rounding=ROUND_HALF_UP)
            if billable_amount != expected_amount:
                raise ValueError("Completed-work billable amount must equal quantity times billable rate.")
            try:
                invoice_date = date.fromisoformat(str(self.details["source_invoice_date"]))
            except ValueError as exc:
                raise ValueError("Completed work requires a valid source invoice date.") from exc
            date_basis = self.details.get("record_date_basis")
            source_work_date = self.details.get("source_work_date")
            if date_basis == "source_work_date":
                try:
                    parsed_work_date = date.fromisoformat(str(source_work_date or ""))
                except ValueError as exc:
                    raise ValueError("Source-dated completed work requires a valid source work date.") from exc
                if parsed_work_date != self.work_date:
                    raise ValueError("Completed-work date must match the source work date.")
            elif date_basis == "invoice_date_reference_only":
                if source_work_date:
                    raise ValueError("Invoice-date reference records cannot claim a source work date.")
                if self.work_date != invoice_date:
                    raise ValueError("Invoice-date reference records must use the source invoice date.")
            else:
                raise ValueError("Completed work requires a valid record date basis.")
        return self


class FieldRecordRead(FieldRecordCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submitted_by: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PurchaseOrderInvoiceAttach(BaseModel):
    document_id: UUID
    invoice_number: str = Field(min_length=1, max_length=120)
    vendor_name: str = Field(min_length=1, max_length=255)
    invoice_date: date
    subtotal: float = Field(ge=0)
    tax: float = Field(ge=0)
    total: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_invoice_total(self) -> "PurchaseOrderInvoiceAttach":
        if abs((self.subtotal + self.tax) - self.total) > 0.02:
            raise ValueError("Invoice subtotal plus tax must equal the total.")
        return self


class PurchaseOrderInvoiceDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_rejection_note(self) -> "PurchaseOrderInvoiceDecision":
        if self.decision == "rejected" and not str(self.note or "").strip():
            raise ValueError("A rejection note is required.")
        return self


class SignatureCreate(BaseModel):
    employee_id: UUID
    employee_name: str = Field(min_length=1, max_length=255)
    acknowledgement: str = Field(default="I acknowledge and understand this record.", min_length=10, max_length=1000)
    supervised_shared_device: bool = False
    worker_confirmation: bool = False
    supervisor_confirmation: str | None = Field(default=None, max_length=500)


class FLHAUpdate(BaseModel):
    project_id: UUID | None = None
    work_date: date
    title: str = Field(min_length=1, max_length=255)
    details: dict = Field(default_factory=dict)
    document_ids: list[UUID] = Field(default_factory=list)


class FLHAReassessment(FLHAUpdate):
    reason: str = Field(min_length=3, max_length=1000)
    changed_conditions: list[Literal["scope", "weather", "crew", "equipment", "conditions"]] = Field(min_length=1)


class FLHARelease(BaseModel):
    verification: str = Field(min_length=10, max_length=1000)


class SafetyRecordUpdate(BaseModel):
    status: Literal[
        "blocked",
        "at_risk",
        "ready",
        "open",
        "verification",
        "reported",
        "under_review",
        "closed",
    ]
    evidence: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def require_evidence_for_completion(self) -> "SafetyRecordUpdate":
        if self.status in {"ready", "verification", "under_review", "closed"} and not (self.evidence or "").strip():
            raise ValueError("Verification evidence is required for that status.")
        return self


class MilestoneDecision(BaseModel):
    decision: Literal["approved", "declined"]
    practical_passed: bool = False
    practical_notes: str | None = None
    reward_type: Literal["none", "bonus", "gift", "training", "paid_time", "other"] = "none"
    reward_description: str | None = None


class TimeOffDecision(BaseModel):
    decision: Literal["approved", "declined"]
    management_notes: str | None = Field(default=None, max_length=2000)


class ToolboxTalk(BaseModel):
    week_of: date
    title: str
    summary: str
    discussion_points: list[str]
    source_name: str
    source_url: str


class SafetyAnalytics(BaseModel):
    as_of: date
    safety_controls_total: int
    blocked_permits: int
    at_risk_permits: int
    open_corrective_actions: int
    overdue_corrective_actions: int
    active_emergency_cards: int
    flha_last_30_days: int
    toolbox_talks_last_30_days: int
    open_incidents: int
    credentials_expiring_60_days: int
    credentials_expired: int
    audit_export_records: int
    confidential_record_types_excluded: list[str]


class OperatorAssignmentRead(BaseModel):
    resource_type: Literal["equipment", "vehicle"]
    resource_id: UUID
    name: str
    status: str


class OperatorAccessRead(BaseModel):
    authorized: bool
    employee_id: UUID | None
    blockers: list[str]
    assignments: list[OperatorAssignmentRead]
    orientation_status: Literal["Ready", "Blocked", "Supervised work only", "Not recorded"]
    qualification_record_id: UUID | None


class FieldOperationsBootstrap(BaseModel):
    employees: list[EmployeeRead]
    projects: list[dict]
    suppliers: list[dict]
    equipment: list[dict]
    cost_codes: list[dict]
    job_workbooks: list[dict]
    production_items: list[dict]
    material_types: list[dict]
    material_movement_summary: list[dict]
    milestone_catalog: list[dict]
    milestone_recognitions: list[dict]
    paperwork_recognitions: list[dict]
    vehicles: list[VehicleRead]
    vehicle_logs: list[VehicleLogRead]
    time_entries: list[TimeEntryRead]
    records: list[FieldRecordRead]
    certifications: list[CertificationRead]
    alerts: list[dict]
    toolbox_talk: ToolboxTalk
    flha_presets: list[dict]
    operator_access: OperatorAccessRead
