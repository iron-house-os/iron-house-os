from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ProjectSafetyRecordRequirement(BaseModel):
    code: str
    label: str
    applicability_status: Literal["unconfirmed", "applicable", "not_applicable"]
    status: Literal["not_started", "in_progress", "blocked", "ready"]
    record_id: UUID | None
    evidence_document_ids: list[UUID]


class ProjectPortalAssignment(BaseModel):
    employee_id: UUID
    portal_role: Literal["employee", "operator", "foreman"]
    status: Literal["active", "revoked"]


class ProjectPortalAccessControl(BaseModel):
    status: Literal["not_started", "active", "suspended"]
    automatic_provisioning: bool
    assignments: list[ProjectPortalAssignment]


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
