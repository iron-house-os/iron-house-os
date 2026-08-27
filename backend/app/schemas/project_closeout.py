from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ProjectCloseoutChecklistUpdate(BaseModel):
    completed: bool
    evidence: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_completion_evidence(self) -> "ProjectCloseoutChecklistUpdate":
        evidence = str(self.evidence or "").strip()
        if self.completed and not evidence:
            raise ValueError("Completion evidence is required for a closeout control.")
        self.evidence = evidence or None
        return self


class ProjectCloseoutChecklistItemRead(BaseModel):
    code: str
    category: str
    label: str
    sort_order: int
    completed: bool
    evidence: str | None
    changed_by: str | None
    changed_at: datetime | None


class ProjectCloseoutChecklistRead(BaseModel):
    project_id: UUID
    status: Literal["ready", "not_ready"]
    completed_count: int
    total_count: int
    next_incomplete_control: ProjectCloseoutChecklistItemRead | None
    items: list[ProjectCloseoutChecklistItemRead]
