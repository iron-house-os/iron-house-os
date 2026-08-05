from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


BackupStatus = Literal["pending", "processing", "routed", "needs_review", "failed"]
BackupDetectedType = Literal["receipt", "supplier_invoice", "packing_slip", "other"]


class BackupAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: str
    actor_email: str
    from_status: str | None
    to_status: str | None
    detail_json: dict
    created_at: datetime


class BackupIntakeRead(BaseModel):
    id: UUID
    media_asset_id: UUID
    media_sha256: str
    uploader_id: UUID
    uploader_email: str
    uploader_role: str
    uploaded_at: datetime
    note: str | None
    project_hint: str | None
    status: BackupStatus
    detected_type: BackupDetectedType | None
    confidence: float | None
    destination_type: str | None
    destination_record_id: UUID | None
    error: str | None
    sensitive_quarantine: bool
    classifier: str | None
    attempt_count: int
    last_attempt_at: datetime | None
    processing_started_at: datetime | None
    processed_at: datetime | None
    routed_at: datetime | None
    failed_at: datetime | None
    audit_history: list[BackupAuditRead]
    created_at: datetime
    updated_at: datetime


class BackupIntakeList(BaseModel):
    items: list[BackupIntakeRead]
    total: int


class BackupControllerRunRead(BaseModel):
    selected: int
    routed: int
    needs_review: int
    failed: int


class BackupRetryRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
