from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class RFQPackageStatus(StrEnum):
    draft = "draft"
    assembling = "assembling"
    ready = "ready"
    issued = "issued"
    closed = "closed"


class RFQRecipientStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    replied = "replied"
    bounced = "bounced"


class RFQPackageDocumentStatus(StrEnum):
    pending = "pending"
    attached = "attached"
    not_applicable = "not_applicable"


class SupplierRecipientCreate(BaseModel):
    supplier_id: str = Field(min_length=1)
    supplier_name: str = Field(min_length=1)
    category: str | None = None
    scope_items: list[str] = Field(default_factory=list)


class SupplierRecipientRead(SupplierRecipientCreate):
    id: UUID
    status: RFQRecipientStatus
    scope_summary: str | None = None
    status_note: str | None = None


class SupplierRecipientStatusUpdate(BaseModel):
    status: RFQRecipientStatus
    note: str | None = None


class RFQPackageDocumentCreate(BaseModel):
    document_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    required: bool = True
    storage_uri: str | None = None
    status: RFQPackageDocumentStatus = RFQPackageDocumentStatus.pending
    metadata: dict = Field(default_factory=dict)


class RFQPackageDocumentRead(RFQPackageDocumentCreate):
    id: UUID


class RFQPackageDocumentStatusUpdate(BaseModel):
    status: RFQPackageDocumentStatus
    storage_uri: str | None = None


class RFQPackageCreate(BaseModel):
    title: str = Field(min_length=1)
    project_id: UUID | None = None
    project_name: str | None = None
    scope_summary: str | None = None
    due_at: datetime | None = None
    supplier_category_targets: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class RFQPackageUpdateStatus(BaseModel):
    status: RFQPackageStatus


class RFQPackageRead(BaseModel):
    id: UUID
    project_id: UUID | None
    title: str
    project_name: str | None
    scope_summary: str | None
    due_at: datetime | None
    status: RFQPackageStatus
    supplier_category_targets: list[str]
    metadata: dict
    recipients: list[SupplierRecipientRead] = Field(default_factory=list)
    documents: list[RFQPackageDocumentRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RFQPackageList(BaseModel):
    items: list[RFQPackageRead]
    total: int


class RFQReadinessItem(BaseModel):
    key: str
    label: str
    ready: bool
    detail: str


class RFQPackageReadiness(BaseModel):
    rfq_package_id: UUID
    status: RFQPackageStatus
    ready: bool
    score: int
    items: list[RFQReadinessItem]


class RFQScopeGenerationRequest(BaseModel):
    force: bool = False


class SupplierRFQPackageDraft(BaseModel):
    recipient_id: UUID
    supplier_id: str
    supplier_name: str
    category: str | None = None
    status: RFQRecipientStatus
    subject: str
    body: str
    scope_items: list[str]
    attachment_names: list[str]


class RFQPackageBuildResponse(BaseModel):
    rfq_package_id: UUID
    ready: bool
    blockers: list[str] = Field(default_factory=list)
    packages: list[SupplierRFQPackageDraft] = Field(default_factory=list)
