from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class EmploymentCategory(StrEnum):
    FIELD_STAFF = "field_staff"
    OFFICE_STAFF = "office_staff"


class EmploymentPosition(StrEnum):
    GREEN_LABOURER = "green_labourer"
    LABOURER = "labourer"
    SKILLED_LABOURER = "skilled_labourer"
    JUNIOR_PIPELAYER = "junior_pipelayer"
    SENIOR_PIPELAYER = "senior_pipelayer"
    GRADEMAN_TOP_MAN = "grademan_top_man"
    FOREMAN = "foreman"
    SUPERINTENDENT = "superintendent"
    ADMIN = "admin"
    CONTROLLER = "controller"
    PROJECT_MANAGER = "project_manager"
    COO = "coo"
    CEO = "ceo"


FIELD_POSITIONS = {
    EmploymentPosition.GREEN_LABOURER,
    EmploymentPosition.LABOURER,
    EmploymentPosition.SKILLED_LABOURER,
    EmploymentPosition.JUNIOR_PIPELAYER,
    EmploymentPosition.SENIOR_PIPELAYER,
    EmploymentPosition.GRADEMAN_TOP_MAN,
    EmploymentPosition.FOREMAN,
    EmploymentPosition.SUPERINTENDENT,
}
OFFICE_POSITIONS = {
    EmploymentPosition.ADMIN,
    EmploymentPosition.CONTROLLER,
    EmploymentPosition.PROJECT_MANAGER,
    EmploymentPosition.COO,
    EmploymentPosition.CEO,
}


class OnboardingStatus(StrEnum):
    DRAFT = "draft"
    INVITATION_SENT = "invitation_sent"
    INVITATION_OPENED = "invitation_opened"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    CORRECTIONS_REQUIRED = "corrections_required"
    APPROVED = "approved"
    ACTIVE = "active"
    INVITATION_EXPIRED = "invitation_expired"
    CANCELLED = "cancelled"


class EmployeeOnboardingCreate(BaseModel):
    legal_first_name: str = Field(min_length=1, max_length=100)
    legal_last_name: str = Field(min_length=1, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    personal_email: EmailStr
    mobile_phone: str | None = Field(default=None, max_length=40)
    category: EmploymentCategory
    position: EmploymentPosition
    supervisor_id: UUID | None = None
    employment_type: str = Field(min_length=1, max_length=50)
    start_date: date
    primary_location: str | None = Field(default=None, max_length=150)
    onboarding_package: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_position_category(self) -> EmployeeOnboardingCreate:
        valid_positions = FIELD_POSITIONS if self.category == EmploymentCategory.FIELD_STAFF else OFFICE_POSITIONS
        if self.position not in valid_positions:
            raise ValueError("Position does not belong to the selected employment category.")
        return self


class EmployeeOnboardingUpdate(BaseModel):
    preferred_name: str | None = Field(default=None, max_length=100)
    mobile_phone: str | None = Field(default=None, max_length=40)
    supervisor_id: UUID | None = None
    primary_location: str | None = Field(default=None, max_length=150)
    onboarding_package: str | None = Field(default=None, max_length=100)


class EmployeeOnboardingRead(BaseModel):
    id: UUID
    legal_first_name: str
    legal_last_name: str
    preferred_name: str | None
    personal_email: EmailStr
    mobile_phone: str | None
    category: EmploymentCategory
    position: EmploymentPosition
    supervisor_id: UUID | None
    employment_type: str
    start_date: date
    primary_location: str | None
    onboarding_package: str | None
    status: OnboardingStatus
    completion_percent: int
    missing_items: list[str]
    reviewer_id: UUID | None
    correction_note: str | None
    invitation_expires_at: datetime | None
    invited_at: datetime | None
    submitted_at: datetime | None
    approved_at: datetime | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeOnboardingList(BaseModel):
    items: list[EmployeeOnboardingRead]
    total: int


class InvitationRead(BaseModel):
    onboarding_id: UUID
    invite_url: str
    expires_at: datetime


class CorrectionRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class PortalProgressUpdate(BaseModel):
    completed_items: list[str] = Field(default_factory=list)


class PortalSubmission(BaseModel):
    completed_items: list[str]
    acknowledgement: bool


class PositionOption(BaseModel):
    value: EmploymentPosition
    label: str
    category: EmploymentCategory
    level: int


POSITION_OPTIONS = [
    PositionOption(value=EmploymentPosition.GREEN_LABOURER, label="Green Labourer", category=EmploymentCategory.FIELD_STAFF, level=1),
    PositionOption(value=EmploymentPosition.LABOURER, label="Labourer", category=EmploymentCategory.FIELD_STAFF, level=2),
    PositionOption(value=EmploymentPosition.SKILLED_LABOURER, label="Skilled Labourer", category=EmploymentCategory.FIELD_STAFF, level=3),
    PositionOption(value=EmploymentPosition.JUNIOR_PIPELAYER, label="Junior Pipelayer", category=EmploymentCategory.FIELD_STAFF, level=4),
    PositionOption(value=EmploymentPosition.SENIOR_PIPELAYER, label="Senior Pipelayer", category=EmploymentCategory.FIELD_STAFF, level=5),
    PositionOption(value=EmploymentPosition.GRADEMAN_TOP_MAN, label="Grademan / Top Man", category=EmploymentCategory.FIELD_STAFF, level=6),
    PositionOption(value=EmploymentPosition.FOREMAN, label="Foreman", category=EmploymentCategory.FIELD_STAFF, level=7),
    PositionOption(value=EmploymentPosition.SUPERINTENDENT, label="Superintendent", category=EmploymentCategory.FIELD_STAFF, level=8),
    PositionOption(value=EmploymentPosition.ADMIN, label="Admin", category=EmploymentCategory.OFFICE_STAFF, level=1),
    PositionOption(value=EmploymentPosition.CONTROLLER, label="Controller", category=EmploymentCategory.OFFICE_STAFF, level=2),
    PositionOption(value=EmploymentPosition.PROJECT_MANAGER, label="Project Manager", category=EmploymentCategory.OFFICE_STAFF, level=3),
    PositionOption(value=EmploymentPosition.COO, label="COO", category=EmploymentCategory.OFFICE_STAFF, level=4),
    PositionOption(value=EmploymentPosition.CEO, label="CEO", category=EmploymentCategory.OFFICE_STAFF, level=5),
]
