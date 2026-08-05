from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class MediaCategory(StrEnum):
    job_photo = "job_photo"
    production_photo = "production_photo"
    inspection = "inspection"
    equipment = "equipment"
    flha = "flha"
    incident = "incident"
    deficiency = "deficiency"
    expense = "expense"
    receipt = "receipt"
    backups = "backups"


class MediaAction(StrEnum):
    original = "original"
    edit = "edit"
    replacement = "replacement"
    restore = "restore"


class MediaOperation(BaseModel):
    type: str
    values: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_supported_operation(self) -> "MediaOperation":
        allowed = {
            "rotate", "straighten", "crop", "brightness", "contrast", "clarity",
            "draw", "arrow", "box", "highlight", "text",
        }
        if self.type not in allowed:
            raise ValueError(f"Unsupported media operation: {self.type}")
        if self.type == "rotate" and self.values.get("degrees") not in {-270, -180, -90, 90, 180, 270}:
            raise ValueError("Rotation must use a supported right angle")
        if self.type == "straighten":
            angle = float(self.values.get("degrees", 0))
            if angle < -15 or angle > 15:
                raise ValueError("Straighten angle must be between -15 and 15 degrees")
        if self.type == "crop":
            required = {"x", "y", "width", "height"}
            if not required.issubset(self.values) or any(float(self.values[key]) < 0 for key in required):
                raise ValueError("Crop requires non-negative x, y, width and height")
        return self


class MediaMetadataUpdate(BaseModel):
    caption: str | None = Field(default=None, max_length=2000)
    captured_date: date | None = None
    project_id: UUID | None = None
    location: str | None = Field(default=None, max_length=255)
    category: MediaCategory | None = None


class MediaLinkCreate(BaseModel):
    record_type: str = Field(min_length=1, max_length=80)
    record_id: UUID


class MediaRestoreRequest(BaseModel):
    version_id: UUID
    amendment_reason: str | None = Field(default=None, max_length=2000)


class MediaVersionRead(BaseModel):
    id: UUID
    asset_id: UUID
    parent_version_id: UUID | None
    document_id: UUID
    version_number: int
    action: MediaAction
    editor_id: UUID
    editor_email: str
    operations: list[MediaOperation]
    change_summary: str | None
    amendment_reason: str | None
    created_at: datetime


class MediaAssetRead(BaseModel):
    id: UUID
    original_document_id: UUID
    current_version_id: UUID
    project_id: UUID | None
    caption: str | None
    captured_date: date | None
    location: str | None
    category: MediaCategory
    controlled: bool
    created_by_email: str
    versions: list[MediaVersionRead]
    links: list[MediaLinkCreate]
    created_at: datetime
    updated_at: datetime
