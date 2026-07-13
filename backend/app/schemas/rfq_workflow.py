from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RFQWorkflowPrepareRequest(BaseModel):
    drive_folder_uri: str = Field(min_length=1)
    drive_manifest_uri: str | None = None
    sender_name: str = "Iron House"
    sender_email: EmailStr | None = None
    sender_phone: str | None = None


class DrivePackageRecord(BaseModel):
    folder_uri: str
    manifest_uri: str | None = None
    reusable: bool = True
    document_references: list[str] = Field(default_factory=list)
    saved_at: datetime
    source_fingerprint: str


class GmailDraftPlan(BaseModel):
    recipient_id: UUID
    supplier_id: str
    supplier_name: str
    to: EmailStr | None = None
    subject: str
    body: str
    attachment_references: list[str] = Field(default_factory=list)
    status: Literal["preview_only"] = "preview_only"
    ready_for_draft_creation: bool
    send_approved: Literal[False] = False


class SupplierResponseCreate(BaseModel):
    supplier_id: str = Field(min_length=1)
    received_at: datetime | None = None
    gmail_thread_uri: str | None = None
    drive_file_uri: str | None = None
    notes: str | None = None


class SupplierResponseRecord(SupplierResponseCreate):
    id: UUID
    supplier_name: str
    received_at: datetime
    recorded_at: datetime


class RFQCommunicationWorkflow(BaseModel):
    rfq_package_id: UUID
    status: Literal["preview_only"] = "preview_only"
    prepared_at: datetime | None = None
    stale: bool = False
    drive_package: DrivePackageRecord | None = None
    gmail_drafts: list[GmailDraftPlan] = Field(default_factory=list)
    supplier_responses: list[SupplierResponseRecord] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    external_actions_performed: Literal[False] = False
    send_requires_approval: Literal[True] = True
