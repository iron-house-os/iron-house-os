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
    voice_supported: bool = True

