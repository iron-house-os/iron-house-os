from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


TimesheetStatus = Literal["draft", "submitted", "needs_review", "approved", "rejected", "exported", "void"]


class LabourSplit(BaseModel):
    cost_code: str = Field(min_length=1, max_length=32)
    straight_time: float = Field(default=0, ge=0, le=24)
    overtime: float = Field(default=0, ge=0, le=24)
    start_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def validate_split(self) -> "LabourSplit":
        if self.straight_time + self.overtime <= 0:
            raise ValueError("Each labour split requires straight-time or overtime hours.")
        if bool(self.start_time) != bool(self.end_time):
            raise ValueError("Enter both start and end time when recording a timed split.")
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("A labour split must end after it starts.")
        return self


class CrewLabourLine(BaseModel):
    employee_id: UUID
    equipment_id: UUID | None = None
    splits: list[LabourSplit] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_splits(self) -> "CrewLabourLine":
        codes = [item.cost_code.strip().upper() for item in self.splits]
        if len(codes) != len(set(codes)):
            raise ValueError("An employee cannot have duplicate cost-code splits.")
        intervals = sorted(
            (item.start_time, item.end_time) for item in self.splits if item.start_time and item.end_time
        )
        if any(current[0] < previous[1] for previous, current in zip(intervals, intervals[1:])):
            raise ValueError("An employee cannot have overlapping timed splits.")
        if sum(item.straight_time + item.overtime for item in self.splits) > 24:
            raise ValueError("An employee's daily hours cannot exceed 24.")
        return self


class EquipmentSplit(BaseModel):
    cost_code: str = Field(min_length=1, max_length=32)
    quantity: float = Field(gt=0, le=9999)


class EquipmentLine(BaseModel):
    source: Literal["owned", "rental"]
    resource_id: UUID
    vendor_id: UUID | None = None
    unit: str = Field(default="hours", min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    splits: list[EquipmentSplit] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_equipment(self) -> "EquipmentLine":
        if self.source == "rental" and self.vendor_id is None:
            raise ValueError("Rental equipment requires an active vendor.")
        codes = [item.cost_code.strip().upper() for item in self.splits]
        if len(codes) != len(set(codes)):
            raise ValueError("Equipment cannot have duplicate cost-code splits.")
        return self


class MaterialProductionLine(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    vendor_id: UUID
    cost_code: str = Field(min_length=1, max_length=32)
    quantity: float = Field(gt=0, le=999999999)
    unit: str = Field(min_length=1, max_length=40)
    production_quantity: float | None = Field(default=None, ge=0, le=999999999)
    production_unit: str | None = Field(default=None, max_length=40)
    receipt_id: UUID | None = None
    document_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_production_unit(self) -> "MaterialProductionLine":
        if self.production_quantity is not None and not self.production_unit:
            raise ValueError("Production quantity requires a unit.")
        return self


class DailyNarrative(BaseModel):
    work_completed: str = Field(default="", max_length=10000)
    delays_issues: str = Field(default="", max_length=10000)
    potential_change: bool = False
    potential_change_details: str = Field(default="", max_length=5000)
    safety_quality_notes: str = Field(default="", max_length=10000)
    general_comments: str = Field(default="", max_length=10000)


class DailyTimesheetWrite(BaseModel):
    work_date: date
    shift: Literal["day", "night"] = "day"
    project_id: UUID
    project_manager_id: UUID | None = None
    supervisor_id: UUID
    weather: str = Field(default="", max_length=500)
    site_conditions: str = Field(default="", max_length=2000)
    document_ids: list[UUID] = Field(default_factory=list)
    ticket_document_ids: list[UUID] = Field(default_factory=list)
    labour: list[CrewLabourLine] = Field(default_factory=list)
    equipment: list[EquipmentLine] = Field(default_factory=list)
    materials: list[MaterialProductionLine] = Field(default_factory=list)
    narrative: DailyNarrative = Field(default_factory=DailyNarrative)

    @model_validator(mode="after")
    def validate_unique_resources(self) -> "DailyTimesheetWrite":
        employee_ids = [item.employee_id for item in self.labour]
        if len(employee_ids) != len(set(employee_ids)):
            raise ValueError("Each employee can appear only once on a daily sheet.")
        equipment_keys = [(item.source, item.resource_id) for item in self.equipment]
        if len(equipment_keys) != len(set(equipment_keys)):
            raise ValueError("Duplicate equipment usage is not allowed on a daily sheet.")
        if len(self.document_ids) != len(set(self.document_ids)):
            raise ValueError("Duplicate field photos are not allowed on a daily sheet.")
        if len(self.ticket_document_ids) != len(set(self.ticket_document_ids)):
            raise ValueError("Duplicate ticket evidence is not allowed on a daily sheet.")
        if set(self.document_ids) & set(self.ticket_document_ids):
            raise ValueError("One attachment cannot be both a field photo and ticket evidence.")
        return self


class DailyTimesheetAction(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class DailyTimesheetRevision(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class DailyTimesheetRead(BaseModel):
    id: UUID
    status: TimesheetStatus
    version: int
    project_id: UUID
    work_date: date
    shift: Literal["day", "night"]
    details: dict
    document_ids: list[UUID]
    ticket_document_ids: list[UUID] = Field(default_factory=list)
    submitted_by: str | None
    created_at: datetime
    updated_at: datetime


class DailyTimesheetBootstrap(BaseModel):
    projects: list[dict]
    employees: list[dict]
    equipment: list[dict]
    rentals: list[dict]
    vendors: list[dict]
    receipts: list[dict]
    project_cost_codes: dict[str, list[dict]]
    assigned_crew: dict[str, list[str]]
    sheets: list[DailyTimesheetRead]
    can_approve: bool
