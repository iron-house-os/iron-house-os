from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.document import DocumentCategory, DocumentRead
from app.schemas.project import ProjectRead
from app.schemas.rfq_package import RFQPackageRead


class TenderStatus(StrEnum):
    new = "new"
    reviewing = "reviewing"
    bidding = "bidding"
    submitted = "submitted"
    awarded = "awarded"
    lost = "lost"
    no_bid = "no_bid"


class TenderDocumentIntake(BaseModel):
    title: str = Field(min_length=1)
    category: DocumentCategory = DocumentCategory.other
    storage_uri: str | None = None
    description: str | None = None
    metadata: dict = Field(default_factory=dict)


class TenderBase(BaseModel):
    title: str = Field(min_length=1)
    tender_number: str | None = None
    source: str | None = None
    source_url: str | None = None
    owner: str | None = None
    municipality: str | None = None
    closing_date: date | None = None
    site_meeting_date: date | None = None
    question_deadline: date | None = None
    project_address: str | None = None
    description: str | None = None
    status: TenderStatus = TenderStatus.new
    estimated_value: float | None = None
    metadata: dict = Field(default_factory=dict)


class TenderCreate(TenderBase):
    project_id: UUID | None = None
    rfq_package_id: UUID | None = None


class TenderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    tender_number: str | None = None
    source: str | None = None
    source_url: str | None = None
    owner: str | None = None
    municipality: str | None = None
    closing_date: date | None = None
    site_meeting_date: date | None = None
    question_deadline: date | None = None
    project_address: str | None = None
    description: str | None = None
    status: TenderStatus | None = None
    estimated_value: float | None = None
    metadata: dict | None = None
    project_id: UUID | None = None
    rfq_package_id: UUID | None = None


class TenderRead(TenderBase):
    id: UUID
    project_id: UUID | None
    rfq_package_id: UUID | None
    document_ids: list[UUID] = Field(default_factory=list)
    suggested_supplier_categories: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TenderList(BaseModel):
    items: list[TenderRead]
    total: int


class TenderIntakeCreate(TenderBase):
    documents: list[TenderDocumentIntake] = Field(default_factory=list)


class TenderIntakeRead(BaseModel):
    tender: TenderRead
    project: ProjectRead
    rfq_package: RFQPackageRead
    documents: list[DocumentRead]
    suggested_supplier_categories: list[str]
