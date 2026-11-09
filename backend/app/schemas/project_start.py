from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ProjectStartChecklistUpdate(BaseModel):
    completed: bool


class ProjectStartChecklistItemRead(BaseModel):
    code: str
    category: str
    label: str
    sort_order: int
    completed: bool
    changed_by: str | None
    changed_at: datetime | None


class ProjectStartChecklistRead(BaseModel):
    project_id: UUID
    status: Literal["ready", "not_ready"]
    completed_count: int
    total_count: int
    items: list[ProjectStartChecklistItemRead]
