from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


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
    EQUIPMENT_OPERATOR = "equipment_operator"
    FOREMAN = "foreman"
    SUPERINTENDENT = "superintendent"
    ADMIN = "admin"
    CONTROLLER = "controller"
    PROJECT_MANAGER = "project_manager"
    CFO = "cfo"
    COO = "coo"
    CEO = "ceo"
    PRESIDENT = "president"


FIELD_POSITIONS = {
    EmploymentPosition.GREEN_LABOURER,
    EmploymentPosition.LABOURER,
    EmploymentPosition.SKILLED_LABOURER,
    EmploymentPosition.JUNIOR_PIPELAYER,
    EmploymentPosition.SENIOR_PIPELAYER,
    EmploymentPosition.GRADEMAN_TOP_MAN,
    EmploymentPosition.EQUIPMENT_OPERATOR,
    EmploymentPosition.FOREMAN,
    EmploymentPosition.SUPERINTENDENT,
}
OFFICE_POSITIONS = {
    EmploymentPosition.ADMIN,
    EmploymentPosition.CONTROLLER,
    EmploymentPosition.PROJECT_MANAGER,
    EmploymentPosition.CFO,
    EmploymentPosition.COO,
    EmploymentPosition.CEO,
    EmploymentPosition.PRESIDENT,
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


class PortalActivationRead(BaseModel):
    onboarding: EmployeeOnboardingRead
    employee_id: UUID
    account_id: UUID
    username: EmailStr
    temporary_password: str
    portal_role: Literal["employee", "operator", "foreman"]


class CorrectionRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class PortalPersonalInformation(BaseModel):
    preferred_name: str | None = Field(default=None, max_length=100)
    mobile_phone: str = Field(min_length=7, max_length=40)
    date_of_birth: date


class PortalAddress(BaseModel):
    street_address: str = Field(min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=40)
    city: str = Field(min_length=1, max_length=100)
    province: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(pattern=r"^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$")
    country: str = Field(default="Canada", min_length=2, max_length=100)


class PortalEmergencyContact(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    relationship: str = Field(min_length=1, max_length=100)
    primary_phone: str = Field(min_length=7, max_length=40)
    alternate_phone: str | None = Field(default=None, max_length=40)


class PortalPayroll(BaseModel):
    payment_method: Literal["direct_deposit", "cheque"]
    account_holder_name: str | None = Field(default=None, max_length=200)
    institution_number: str | None = Field(default=None, pattern=r"^\d{3}$")
    transit_number: str | None = Field(default=None, pattern=r"^\d{5}$")
    account_number: str | None = Field(default=None, pattern=r"^\d{5,17}$")
    direct_deposit_authorized: bool = False

    @model_validator(mode="after")
    def validate_direct_deposit(self) -> PortalPayroll:
        if self.payment_method == "direct_deposit" and not all(
            (
                self.account_holder_name,
                self.institution_number,
                self.transit_number,
                self.account_number,
                self.direct_deposit_authorized,
            )
        ):
            raise ValueError("Complete and authorise every direct-deposit field.")
        return self


class PortalTaxForms(BaseModel):
    form_year: Literal[2026] = 2026
    social_insurance_number: str = Field(pattern=r"^\d{9}$")
    country_of_permanent_residence: str = Field(default="Canada", min_length=2, max_length=100)
    federal_claim_amounts: list[Decimal] = Field(min_length=12, max_length=12)
    bc_claim_amounts: list[Decimal] = Field(min_length=10, max_length=10)
    federal_more_than_one_employer: bool = False
    federal_total_income_less_than_claim: bool = False
    non_resident_world_income_90_percent_or_more: bool | None = None
    additional_tax_per_payment: Decimal = Field(default=Decimal("0"), ge=0)
    bc_more_than_one_employer: bool = False
    bc_total_income_less_than_claim: bool = False
    federal_certified: bool
    bc_certified: bool

    @field_validator("social_insurance_number")
    @classmethod
    def validate_sin(cls, value: str) -> str:
        digits = [int(character) for character in value]
        checksum = 0
        for index, digit in enumerate(digits):
            product = digit * (2 if index % 2 else 1)
            checksum += product // 10 + product % 10
        if checksum % 10:
            raise ValueError("Enter a valid nine-digit Social Insurance Number.")
        return value

    @field_validator("federal_claim_amounts", "bc_claim_amounts")
    @classmethod
    def validate_claim_amounts(cls, values: list[Decimal]) -> list[Decimal]:
        if any(value < 0 for value in values):
            raise ValueError("Tax credit claim amounts cannot be negative.")
        return values

    @model_validator(mode="after")
    def validate_certification(self) -> PortalTaxForms:
        if not self.federal_certified or not self.bc_certified:
            raise ValueError("Both 2026 TD1 certifications are required.")
        is_non_resident = self.country_of_permanent_residence.strip().casefold() != "canada"
        if is_non_resident and self.non_resident_world_income_90_percent_or_more is None:
            raise ValueError(
                "Non-residents must answer the 2026 federal TD1 world-income question."
            )
        if (
            is_non_resident
            and self.non_resident_world_income_90_percent_or_more is False
            and any(self.federal_claim_amounts)
        ):
            raise ValueError(
                "Non-residents who answer no to the 90% world-income question must enter zero "
                "for every federal TD1 claim amount."
            )
        if not is_non_resident and self.non_resident_world_income_90_percent_or_more is not None:
            raise ValueError("The federal TD1 world-income question is for non-residents only.")
        return self


class PortalAgreements(BaseModel):
    employment_terms_reviewed: bool
    company_policies_reviewed: bool
    privacy_notice_reviewed: bool
    purchase_receipt_standard_reviewed: bool
    questions_resolved: bool

    @model_validator(mode="after")
    def validate_acknowledgements(self) -> PortalAgreements:
        if not all(self.model_dump().values()):
            raise ValueError("Review and acknowledge every assigned agreement and policy.")
        return self


class PortalCertification(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    certificate_number: str | None = Field(default=None, max_length=100)
    issuer: str | None = Field(default=None, max_length=160)
    expiry_date: date | None = None


class PortalCertifications(BaseModel):
    none_to_report: bool = False
    certifications: list[PortalCertification] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_certifications(self) -> PortalCertifications:
        if self.none_to_report == bool(self.certifications):
            raise ValueError("Add at least one certification or confirm there are none to report.")
        return self


class PortalPPERequirements(BaseModel):
    site_ppe_required: bool
    boot_size: str | None = Field(default=None, max_length=30)
    glove_size: str | None = Field(default=None, max_length=30)
    shirt_size: str | None = Field(default=None, max_length=30)
    trouser_size: str | None = Field(default=None, max_length=30)
    prescription_safety_glasses: bool = False
    respirator_fit_test_required: bool = False
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_site_sizes(self) -> PortalPPERequirements:
        if self.site_ppe_required and not all(
            (self.boot_size, self.glove_size, self.shirt_size, self.trouser_size)
        ):
            raise ValueError("Provide all PPE sizes when site PPE is required.")
        return self


class PortalPacket(BaseModel):
    personal_information: PortalPersonalInformation | None = None
    address: PortalAddress | None = None
    emergency_contact: PortalEmergencyContact | None = None
    payroll: PortalPayroll | None = None
    tax_forms: PortalTaxForms | None = None
    employment_agreements: PortalAgreements | None = None
    certifications: PortalCertifications | None = None
    ppe_requirements: PortalPPERequirements | None = None
    signature_name: str | None = Field(default=None, max_length=200)
    signed_at: datetime | None = None


class PortalOnboardingRead(BaseModel):
    onboarding: EmployeeOnboardingRead
    packet: PortalPacket


class PortalProgressUpdate(BaseModel):
    packet: PortalPacket


class PortalSubmission(BaseModel):
    packet: PortalPacket
    acknowledgement: bool
    signature_name: str = Field(min_length=1, max_length=200)


OrientationScope = Literal["company", "site"]
OrientationTrigger = Literal[
    "new_hire",
    "new_site",
    "changed_hazards",
    "new_task",
    "unsafe_performance",
    "worker_request",
    "qualification_expiry",
    "refresher",
]
CompetencyResult = Literal["passed", "requires_supervision", "not_assessed"]

REQUIRED_ORIENTATION_TOPIC_CODES = (
    "supervisor_contact",
    "rights_and_responsibilities",
    "workplace_safety_rules",
    "workplace_hazards",
    "working_alone",
    "violence_prevention",
    "personal_protective_equipment",
    "first_aid",
    "emergency_procedures",
    "task_instruction_and_demonstration",
    "occupational_health_and_safety_program",
    "whmis",
    "committee_or_representative",
)


class OrientationTopic(BaseModel):
    code: Literal[
        "supervisor_contact",
        "rights_and_responsibilities",
        "workplace_safety_rules",
        "workplace_hazards",
        "working_alone",
        "violence_prevention",
        "personal_protective_equipment",
        "first_aid",
        "emergency_procedures",
        "task_instruction_and_demonstration",
        "occupational_health_and_safety_program",
        "whmis",
        "committee_or_representative",
    ]
    applicability: Literal["applicable", "not_applicable"]
    evidence: str | None = Field(default=None, max_length=2000)
    not_applicable_basis: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_evidence(self) -> OrientationTopic:
        if self.applicability == "applicable" and not (self.evidence or "").strip():
            raise ValueError("Evidence is required for each applicable orientation topic.")
        if self.applicability == "not_applicable" and not (self.not_applicable_basis or "").strip():
            raise ValueError("A basis is required when an orientation topic is not applicable.")
        return self


class WorkerOrientationCreate(BaseModel):
    project_id: UUID | None = None
    scope: OrientationScope
    site_name: str | None = Field(default=None, max_length=255)
    trigger: OrientationTrigger
    orientation_date: date
    instructor_name: str = Field(min_length=1, max_length=200)
    instructor_email: EmailStr | None = None
    supervisor_name: str = Field(min_length=1, max_length=200)
    supervisor_email: EmailStr | None = None
    document_version: str = Field(min_length=1, max_length=80)
    topics: list[OrientationTopic]
    competency_result: CompetencyResult
    ppe_verified: bool
    qualifications_verified: bool
    worker_acknowledged: bool
    worker_acknowledged_at: datetime | None = None
    supporting_document_ids: list[UUID] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_record(self) -> WorkerOrientationCreate:
        if self.scope == "site" and self.project_id is None and not (self.site_name or "").strip():
            raise ValueError("A project or site name is required for site orientation.")
        codes = [topic.code for topic in self.topics]
        if len(codes) != len(set(codes)) or set(codes) != set(REQUIRED_ORIENTATION_TOPIC_CODES):
            raise ValueError("Each required orientation topic must be recorded exactly once.")
        if self.worker_acknowledged and self.worker_acknowledged_at is None:
            raise ValueError("Worker acknowledgement time is required when acknowledged.")
        if not self.worker_acknowledged and self.worker_acknowledged_at is not None:
            raise ValueError("Worker acknowledgement time cannot be set before acknowledgement.")
        return self


class WorkerOrientationRead(WorkerOrientationCreate):
    id: UUID
    onboarding_id: UUID
    created_by: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeploymentStatusRead(BaseModel):
    status: Literal["Blocked", "Supervised work only", "Ready"]
    blockers: list[str]
    latest_company_orientation_id: UUID | None = None
    latest_site_orientation_id: UUID | None = None


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
    PositionOption(value=EmploymentPosition.EQUIPMENT_OPERATOR, label="Equipment Operator", category=EmploymentCategory.FIELD_STAFF, level=7),
    PositionOption(value=EmploymentPosition.FOREMAN, label="Foreman", category=EmploymentCategory.FIELD_STAFF, level=8),
    PositionOption(value=EmploymentPosition.SUPERINTENDENT, label="Superintendent", category=EmploymentCategory.FIELD_STAFF, level=9),
    PositionOption(value=EmploymentPosition.ADMIN, label="Admin", category=EmploymentCategory.OFFICE_STAFF, level=1),
    PositionOption(value=EmploymentPosition.CONTROLLER, label="Controller", category=EmploymentCategory.OFFICE_STAFF, level=2),
    PositionOption(value=EmploymentPosition.PROJECT_MANAGER, label="Project Manager", category=EmploymentCategory.OFFICE_STAFF, level=3),
    PositionOption(value=EmploymentPosition.CFO, label="CFO", category=EmploymentCategory.OFFICE_STAFF, level=4),
    PositionOption(value=EmploymentPosition.COO, label="COO", category=EmploymentCategory.OFFICE_STAFF, level=5),
    PositionOption(value=EmploymentPosition.CEO, label="CEO", category=EmploymentCategory.OFFICE_STAFF, level=6),
    PositionOption(value=EmploymentPosition.PRESIDENT, label="President", category=EmploymentCategory.OFFICE_STAFF, level=7),
]
