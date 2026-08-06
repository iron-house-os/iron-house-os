from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


BackupsStatus = Literal["pending", "processing", "routed", "needs_review", "failed"]
BackupsDetectedType = Literal["receipt", "supplier_invoice", "packing_slip", "other"]
BackupsReviewDestination = Literal[
    "finance_intake",
    "finance_receipts",
    "finance_invoices",
    "finance_packing_slips",
    "backups_needs_review",
]


class BackupsIntakeCreate(BaseModel):
    media_id: UUID
    note: str | None = Field(default=None, max_length=2000)
    project_hint: str | None = Field(default=None, max_length=255)


class BackupsAuditRead(BaseModel):
    id: UUID
    action: str
    actor_email: str
    from_status: str | None
    to_status: str | None
    details: dict
    created_at: datetime


class BackupsDestinationUpdate(BaseModel):
    destination: Literal["finance_receipts", "finance_invoices", "finance_packing_slips", "backups_needs_review"]
    expected_version: int = Field(ge=0)


class BackupsIntakeRead(BaseModel):
    id: UUID
    media_id: UUID
    media_hash: str
    uploader_id: UUID
    uploader_email: str
    uploader_role: str
    upload_timestamp: datetime
    note: str | None
    project_hint: str | None
    status: BackupsStatus
    detected_type: BackupsDetectedType | None
    confidence: float | None
    classification_source: str | None
    review_destination: BackupsReviewDestination | None
    routing_version: int
    destination_type: str | None
    destination_record_id: UUID | None
    error: str | None
    sensitive_quarantine: bool
    attempt_count: int
    last_attempt_at: datetime | None
    processing_started_at: datetime | None
    processed_at: datetime | None
    routed_at: datetime | None
    failed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    audit_history: list[BackupsAuditRead]


class BackupsIntakeList(BaseModel):
    items: list[BackupsIntakeRead]
    total: int


class BackupsControllerResult(BaseModel):
    claimed: int
    routed: int
    needs_review: int
    failed: int
