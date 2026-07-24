from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LegalMatterCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    matter_type: str = Field(min_length=2, max_length=60)
    project_name: str | None = Field(default=None, max_length=200)
    counterparty: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=10, max_length=12000)
    confidentiality: str = Field(default="standard", pattern="^(standard|personal_information|privilege_requested)$")
    jurisdiction: str = Field(default="British Columbia, Canada", max_length=80)


class LegalAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    matter_id: UUID
    requested_by: str
    status: str
    specialist_keys: list[str]
    executive_summary: str
    draft_text: str | None
    issues: list[dict]
    recommendations: list[dict]
    questions_for_counsel: list[str]
    source_ids: list[str]
    disclaimer: str
    created_at: datetime


class LegalDeadlineCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    due_date: date
    source_basis: str = Field(min_length=5, max_length=4000)


class LegalDeadlineVerify(BaseModel):
    evidence_reference: str = Field(min_length=5, max_length=1000)


class LegalDeadlineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    matter_id: UUID
    title: str
    due_date: date
    source_basis: str
    status: str
    created_by: str
    verified_by: str | None
    verified_at: datetime | None
    evidence_reference: str | None
    created_at: datetime


class LegalMatterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    matter_type: str
    project_name: str | None
    counterparty: str | None
    description: str
    status: str
    risk_level: str
    confidentiality: str
    jurisdiction: str
    assigned_specialists: list[str]
    created_by: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LegalMatterDetail(LegalMatterRead):
    analyses: list[LegalAnalysisRead]
    deadlines: list[LegalDeadlineRead]


class LegalAnalysisRequest(BaseModel):
    question: str | None = Field(default=None, max_length=4000)


class LegalDashboard(BaseModel):
    enabled: bool
    configured: bool
    mode: str
    matters: list[LegalMatterRead]
    specialists: list[dict]
    authorities: list[dict]
    candidate_deadline_count: int
