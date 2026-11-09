from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.estimate import EstimateCreate, EstimateSummary


class EstimateWorkspaceSaveRequest(BaseModel):
    project_id: UUID
    tender_id: UUID | None = None
    status: str = Field(default="draft", min_length=1)
    estimate: EstimateCreate
    summary: EstimateSummary | None = None


class EstimateWorkspaceRead(BaseModel):
    id: UUID
    project_id: UUID
    tender_id: UUID | None
    status: str
    total_amount: float | None
    summary_text: str | None
    estimate: dict
    created_at: datetime
    updated_at: datetime


class EstimateWorkspaceList(BaseModel):
    items: list[EstimateWorkspaceRead]
    total: int
