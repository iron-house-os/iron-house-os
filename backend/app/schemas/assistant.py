from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssistantConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AssistantMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    status: str
    created_at: datetime


class AssistantPrompt(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class AssistantReply(BaseModel):
    conversation: AssistantConversationRead
    user_message: AssistantMessageRead
    assistant_message: AssistantMessageRead


class AssistantStatus(BaseModel):
    enabled: bool
    configured: bool
    model: str
    mode: str
    memory_count: int = 0


class ProjectMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_kind: str
    source_id: str
    title: str
    content: str
    authority: int
    source_date: datetime | None
    source_url: str | None
    imported_by: str
    created_at: datetime
    updated_at: datetime


class MemoryImportResult(BaseModel):
    imported: int
    updated: int
    skipped: int
    total_project_memories: int


class HelpCoachPrompt(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    route: str = Field(default="", max_length=300, pattern=r"^$|^/[A-Za-z0-9_./:-]*$")
    project_name: str = Field(default="", max_length=160)


class HelpCoachSource(BaseModel):
    id: str
    title: str
    path: str


class HelpCoachReply(BaseModel):
    answer: str
    status: str
    audience: str
    mode: str = "read-only"
    sources: list[HelpCoachSource]
