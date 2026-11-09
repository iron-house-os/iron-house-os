from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


HelpFeedbackType = Literal["helpful", "not_helpful", "stuck", "suggestion"]
HelpImprovementStatus = Literal["new", "reviewing", "planned", "dismissed"]


class HelpFeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_type: HelpFeedbackType
    route: str = Field(default="", max_length=300, pattern=r"^$|^/[A-Za-z0-9_./:-]*$")
    project_name: str = Field(default="", max_length=160)
    source_ids: list[str] = Field(default_factory=list, max_length=8)
    note: str | None = Field(default=None, max_length=600)

    @field_validator("source_ids")
    @classmethod
    def validate_source_ids(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Help source IDs must be unique.")
        if any(len(value) > 100 for value in cleaned):
            raise ValueError("A Help source ID is too long.")
        return cleaned

    @model_validator(mode="after")
    def validate_note(self) -> "HelpFeedbackCreate":
        cleaned = self.note.strip() if self.note else None
        if self.feedback_type == "suggestion" and not cleaned:
            raise ValueError("Tell us what you would improve.")
        self.note = cleaned
        self.project_name = self.project_name.strip()
        return self


class HelpFeedbackReceipt(BaseModel):
    recorded: bool = True
    improvement_id: UUID
    status: str = "recorded"
    message: str = "Thank you. Management will review this Help feedback."


class HelpImprovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feedback_type: HelpFeedbackType
    route: str
    source_ids: list[str]
    status: HelpImprovementStatus
    evidence_count: int
    last_seen_at: datetime
    latest_note: str | None
    latest_project_name: str | None
    review_note: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None


class HelpImprovementList(BaseModel):
    items: list[HelpImprovementRead]
    total: int


class HelpFeedbackEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    audience: str
    project_name: str | None
    note: str | None
    created_at: datetime


class HelpFeedbackEvidenceList(BaseModel):
    items: list[HelpFeedbackEvidenceRead]
    total: int


class HelpImprovementStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: HelpImprovementStatus
    review_note: str | None = Field(default=None, max_length=600)

    @field_validator("review_note")
    @classmethod
    def strip_review_note(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None
