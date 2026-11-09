from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


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
    attendees: list[str] = Field(default_factory=list)
    reminder_minutes: list[int] = Field(default_factory=list)


class GoogleCalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=500)
    start: datetime
    end: datetime
    project_id: UUID | None = None
    attendees: list[str] = Field(default_factory=list, max_length=20)
    reminder_minutes: list[int] = Field(default_factory=lambda: [30], max_length=5)
    send_invitations: bool = False
    confirmed: bool

    @field_validator("attendees")
    @classmethod
    def validate_attendees(cls, values: list[str]) -> list[str]:
        normalised: list[str] = []
        for value in values:
            email = value.strip().lower()
            if not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                raise ValueError("Each attendee must have a valid email address.")
            if email not in normalised:
                normalised.append(email)
        return normalised

    @field_validator("reminder_minutes")
    @classmethod
    def validate_reminders(cls, values: list[int]) -> list[int]:
        if any(value < 0 or value > 40320 for value in values):
            raise ValueError("Reminders must be between 0 minutes and 4 weeks.")
        return sorted(set(values))

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
        if self.attendees and not self.send_invitations:
            raise ValueError("Confirm attendee invitations before adding attendees.")
        return self


class GoogleCalendarEventUpdate(GoogleCalendarEventCreate):
    pass


class GoogleCalendarEventCancel(BaseModel):
    notify_attendees: bool = True
    confirmed: bool


class GoogleCalendarConflictCheck(BaseModel):
    start: datetime
    end: datetime
    exclude_event_id: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def validate_time_range(self):
        if (
            self.start.tzinfo is None
            or self.start.utcoffset() is None
            or self.end.tzinfo is None
            or self.end.utcoffset() is None
        ):
            raise ValueError("Conflict check times must include a time zone.")
        if self.end <= self.start:
            raise ValueError("Conflict check end must be after its start.")
        return self


class GoogleCalendarConflictResult(BaseModel):
    has_conflicts: bool
    conflicts: list[GoogleCalendarEvent]


class GoogleCalendarDisconnect(BaseModel):
    confirmed: bool
