from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentCategory(StrEnum):
    drawing = "drawing"
    specification = "specification"
    addendum = "addendum"
    geotechnical = "geotechnical"
    permit = "permit"
    traffic_control = "traffic_control"
    environmental = "environmental"
    quote_request = "quote_request"
    quote = "quote"
    photo = "photo"
    testing = "testing"
    other = "other"


class DocumentStatus(StrEnum):
    registered = "registered"
    active = "active"
    current = "current"
    superseded = "superseded"
    archived = "archived"


class DrawingMetadata(BaseModel):
    sheet_number: str | None = None
    title: str | None = None
    discipline: str | None = None
    revision: str | None = None
    issue_date: date | None = None
    storage_uri: str | None = None


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1)
    category: DocumentCategory
    status: DocumentStatus = DocumentStatus.registered
    project_id: UUID | None = None
    rfq_package_id: UUID | None = None
    tender_id: UUID | None = None
    supplier_id: UUID | None = None
    storage_uri: str | None = None
    description: str | None = None
    drawing: DrawingMetadata | None = None
    metadata: dict = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    category: DocumentCategory | None = None
    status: DocumentStatus | None = None
    project_id: UUID | None = None
    rfq_package_id: UUID | None = None
    tender_id: UUID | None = None
    supplier_id: UUID | None = None
    storage_uri: str | None = None
    description: str | None = None
    drawing: DrawingMetadata | None = None
    metadata: dict | None = None


class DocumentUpdateStatus(BaseModel):
    status: DocumentStatus


class DocumentUploadResponse(BaseModel):
    document: "DocumentRead"
    original_filename: str
    safe_filename: str
    extension: str
    content_type: str | None
    size_bytes: int
    sha256_hash: str
    duplicate_document_ids: list[UUID]


class DocumentIntegrity(BaseModel):
    document_id: UUID
    storage_uri: str | None
    file_exists: bool
    sha256_hash: str | None
    size_bytes: int | None
    duplicate_document_ids: list[UUID]


class RFQAttachmentManifestRequest(BaseModel):
    document_ids: list[UUID] = Field(default_factory=list)


class RFQAttachmentManifestItem(BaseModel):
    document_id: UUID
    title: str
    category: DocumentCategory
    status: DocumentStatus
    storage_uri: str | None
    filename: str | None
    size_bytes: int | None
    sha256_hash: str | None


class RFQAttachmentManifest(BaseModel):
    item_count: int
    total_size_bytes: int
    items: list[RFQAttachmentManifestItem]
    warnings: list[str]


class DocumentRead(BaseModel):
    id: UUID
    title: str
    category: DocumentCategory
    status: DocumentStatus
    project_id: UUID | None
    rfq_package_id: UUID | None
    tender_id: UUID | None
    supplier_id: UUID | None
    storage_uri: str | None
    description: str | None
    drawing: DrawingMetadata | None
    metadata: dict
    created_at: datetime
    updated_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int
