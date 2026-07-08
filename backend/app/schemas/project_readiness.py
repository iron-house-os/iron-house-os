from uuid import UUID

from pydantic import BaseModel


class ReadinessItem(BaseModel):
    label: str
    status: str
    detail: str
    priority: int


class ProjectReadinessResponse(BaseModel):
    project_id: UUID
    readiness_score: int
    status: str
    items: list[ReadinessItem]
    blockers: list[str]
    next_actions: list[str]
