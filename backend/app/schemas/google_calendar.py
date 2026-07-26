from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class GoogleCalendarStatus(BaseModel):
    enabled: bool
    configured: bool
    connected: bool
    status: str
    required_scope: str
    last_synced_at: datetime | None = None
    last_error: str | None = None


class GoogleCalendarAuthorization(BaseModel):
    authorization_url: str


class GoogleCalendarEvent(BaseModel):
    id: str
    title: str
    description: str | None = None
    location: str | None = None
    start: str
    end: str
    html_link: str | None = None
    status: str
    project_id: UUID | None = None


class GoogleCalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=500)
    start: datetime
    end: datetime
    project_id: UUID | None = None
    confirmed: bool

    @model_validator(mode="after")
    def validate_time_range(self):
        if not self.title.strip():
            raise ValueError("Event title cannot be blank.")
        if (
            self.start.tzinfo is None
            or self.start.utcoffset() is None
            or self.end.tzinfo is None
            or self.end.utcoffset() is None
        ):
            raise ValueError("Event start and end must include a time zone.")
        if self.end <= self.start:
            raise ValueError("Event end must be after its start.")
        return self


class GoogleCalendarDisconnect(BaseModel):
    confirmed: bool
