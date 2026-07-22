from datetime import date, datetime
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
    "performance_review",
    "material_quantity",
    "subcontractor",
    "rental_equipment",
    "weather",
]


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


class EmployeeRead(EmployeeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


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


class FieldRecordRead(FieldRecordCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submitted_by: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SignatureCreate(BaseModel):
    employee_id: UUID
    employee_name: str = Field(min_length=1, max_length=255)
    acknowledgement: str = Field(default="I acknowledge and understand this record.", min_length=10)


class ToolboxTalk(BaseModel):
    week_of: date
    title: str
    summary: str
    discussion_points: list[str]
    source_name: str
    source_url: str


class FieldOperationsBootstrap(BaseModel):
    employees: list[EmployeeRead]
    projects: list[dict]
    suppliers: list[dict]
    equipment: list[dict]
    cost_codes: list[dict]
    vehicles: list[VehicleRead]
    vehicle_logs: list[VehicleLogRead]
    time_entries: list[TimeEntryRead]
    records: list[FieldRecordRead]
    certifications: list[CertificationRead]
    alerts: list[dict]
    toolbox_talk: ToolboxTalk
