from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MeetingActionItem(BaseModel):
    task: str = Field(min_length=1, max_length=1000)
    owner: str | None = Field(default=None, max_length=255)
    due_date: date | None = None


class MeetingMinutesDraftRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=200_000)
    title: str = Field(default="Meeting", min_length=1, max_length=200)
    attendees: list[str] = Field(default_factory=list, max_length=100)
    consent_confirmed: bool

    @field_validator("attendees")
    @classmethod
    def clean_attendees(cls, values: list[str]) -> list[str]:
        return [value.strip()[:255] for value in values if value.strip()]


class MeetingMinutesDraft(BaseModel):
    transcript: str
    summary: str
    priority_points: list[str]
    decisions: list[str]
    action_items: list[MeetingActionItem]
    transcription_model: str | None = None
    summary_model: str
    audio_retained: bool = False


class MeetingMinuteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    project_id: UUID | None = None
    meeting_date: datetime
    attendees: list[str] = Field(default_factory=list, max_length=100)
    transcript: str = Field(min_length=1, max_length=200_000)
    summary: str = Field(min_length=1, max_length=30_000)
    priority_points: list[str] = Field(default_factory=list, max_length=100)
    decisions: list[str] = Field(default_factory=list, max_length=100)
    action_items: list[MeetingActionItem] = Field(default_factory=list, max_length=100)
    transcription_model: str | None = Field(default=None, max_length=120)
    summary_model: str = Field(min_length=1, max_length=120)
    consent_confirmed: bool
    review_confirmed: bool

    @field_validator("attendees", "priority_points", "decisions")
    @classmethod
    def clean_lists(cls, values: list[str]) -> list[str]:
        return [value.strip()[:1000] for value in values if value.strip()]


class MeetingMinuteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_account_id: UUID
    project_id: UUID | None
    title: str
    meeting_date: datetime
    attendees: list[str]
    transcript: str
    summary: str
    priority_points: list[str]
    decisions: list[str]
    action_items: list[MeetingActionItem]
    transcription_model: str | None
    summary_model: str
    status: str
    consent_confirmed: bool
    review_confirmed: bool
    audio_retained: bool
    created_by_email: str
    created_at: datetime
    updated_at: datetime


class MeetingMinuteListItem(BaseModel):
    id: UUID
    project_id: UUID | None
    title: str
    meeting_date: datetime
    status: str
    audio_retained: bool
    created_by_email: str
    created_at: datetime


class MeetingMinutesStatus(BaseModel):
    enabled: bool
    configured: bool
    transcription_model: str
    summary_model: str
    max_audio_bytes: int
    audio_retained: bool = False
