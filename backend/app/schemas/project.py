from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectStatus(StrEnum):
    opportunity = "opportunity"
    tendering = "tendering"
    awarded = "awarded"
    construction = "construction"
    completed = "completed"
    archived = "archived"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    client_owner: str | None = None
    municipality: str | None = None
    project_number: str | None = None
    tender_number: str | None = None
    tender_source: str | None = None
    tender_closing_date: date | None = None
    bid_due_date: date | None = None
    estimated_construction_start: date | None = None
    estimated_construction_finish: date | None = None
    project_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    contract_value: float | None = None
    status: ProjectStatus = ProjectStatus.opportunity
    notes: str | None = None
    metadata: dict = Field(default_factory=dict)
    supplier_ids: list[UUID] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    client_owner: str | None = None
    municipality: str | None = None
    project_number: str | None = None
    tender_number: str | None = None
    tender_source: str | None = None
    tender_closing_date: date | None = None
    bid_due_date: date | None = None
    estimated_construction_start: date | None = None
    estimated_construction_finish: date | None = None
    project_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    contract_value: float | None = None
    status: ProjectStatus | None = None
    notes: str | None = None
    metadata: dict | None = None
    supplier_ids: list[UUID] | None = None


class ProjectRead(BaseModel):
    id: UUID
    name: str
    client_owner: str | None
    municipality: str | None
    project_number: str | None
    tender_number: str | None
    tender_source: str | None
    tender_closing_date: date | None
    bid_due_date: date | None
    estimated_construction_start: date | None
    estimated_construction_finish: date | None
    project_address: str | None
    latitude: float | None
    longitude: float | None
    contract_value: float | None
    status: ProjectStatus
    notes: str | None
    metadata: dict
    supplier_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class ProjectList(BaseModel):
    items: list[ProjectRead]
    total: int


class ProjectDashboard(BaseModel):
    project_id: UUID
    rfq_count: int
    supplier_count: int
    document_count: int
    drawing_count: int
    bid_status: str
    readiness_percentage: int
