from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


ProjectSafetyRequirementCode = Literal[
    "project_safety_plan",
    "emergency_action_card",
    "field_hazard_assessment",
    "toolbox_talk",
    "safety_permit",
    "orientation_verification",
]


class ProjectSafetyRecordRequirement(BaseModel):
    code: ProjectSafetyRequirementCode
    label: str
    applicability_status: Literal["unconfirmed", "applicable", "not_applicable"]
    status: Literal["not_started", "in_progress", "blocked", "ready"]
    record_id: UUID | None
    evidence_document_ids: list[UUID]
    not_applicable_basis: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class ProjectPortalAssignment(BaseModel):
    employee_id: UUID
    portal_role: Literal["employee", "operator", "foreman"]
    status: Literal["active", "revoked"]


class ProjectPortalAccessControl(BaseModel):
    status: Literal["not_started", "active", "suspended"]
    automatic_provisioning: bool
    assignments: list[ProjectPortalAssignment]


class ProjectSafetyReviewEvent(BaseModel):
    reviewed_by: str
    reviewed_at: datetime
    review_note: str
    release_status: Literal["blocked", "at_risk", "ready"]
    portal_status: Literal["not_started", "active", "suspended"]
    active_assignment_count: int


class ProjectSafetyLaunchRead(BaseModel):
    project_id: UUID
    job_number: str
    release_status: Literal["blocked", "at_risk", "ready"]
    folder_path: str
    folder_status: Literal["prepared"]
    record_requirements: list[ProjectSafetyRecordRequirement]
    portal_access: ProjectPortalAccessControl
    initialized_by: str
    initialized_at: datetime
    last_reviewed_by: str | None = None
    last_reviewed_at: datetime | None = None
    last_review_note: str | None = None
    review_history: list[ProjectSafetyReviewEvent] = Field(default_factory=list)


class ProjectSafetyRecordRequirementUpdate(BaseModel):
    code: ProjectSafetyRequirementCode
    applicability_status: Literal["unconfirmed", "applicable", "not_applicable"]
    status: Literal["not_started", "in_progress", "blocked", "ready"]
    record_id: UUID | None = None
    evidence_document_ids: list[UUID] = Field(default_factory=list)
    not_applicable_basis: str | None = Field(default=None, max_length=2000)


class ProjectPortalAccessUpdate(BaseModel):
    status: Literal["not_started", "active", "suspended"]
    assignments: list[ProjectPortalAssignment] = Field(default_factory=list)


class ProjectSafetyLaunchUpdate(BaseModel):
    release_status: Literal["blocked", "at_risk", "ready"]
    record_requirements: list[ProjectSafetyRecordRequirementUpdate]
    portal_access: ProjectPortalAccessUpdate
    review_note: str = Field(min_length=10, max_length=2000)
    release_confirmation: bool = False


class ProjectSafetyEvidenceDocument(BaseModel):
    id: UUID
    title: str
    category: str
    status: str


class ProjectSafetyRecordOption(BaseModel):
    id: UUID
    record_type: str
    title: str
    status: str
    work_date: date


class ProjectSafetyEmployeeOption(BaseModel):
    id: UUID
    display_name: str
    portal_role: Literal["employee", "operator", "foreman"]


class ProjectSafetyPostingBlocker(BaseModel):
    code: str
    message: str


class ProjectSafetyLaunchControls(BaseModel):
    launch: ProjectSafetyLaunchRead
    evidence_documents: list[ProjectSafetyEvidenceDocument]
    record_options: list[ProjectSafetyRecordOption]
    active_employees: list[ProjectSafetyEmployeeOption]
    posting_blockers: list[ProjectSafetyPostingBlocker]
