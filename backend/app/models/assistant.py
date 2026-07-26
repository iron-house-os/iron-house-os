from uuid import UUID

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AssistantConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assistant_conversations"

    owner_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="New conversation")


class AssistantMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assistant_messages"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assistant_conversations.id"), nullable=False, index=True
    )
    actor_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")


class ProjectMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_memories"

    source_kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    authority: Mapped[int] = mapped_column(Integer, nullable=False, default=60, index=True)
    source_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    imported_by: Mapped[str] = mapped_column(String(255), nullable=False)


class MeetingMinute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meeting_minutes"

    owner_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    meeting_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attendees_json: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    priority_points_json: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    decisions_json: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    action_items_json: Mapped[list[dict]] = mapped_column(JSONType, nullable=False, default=list)
    transcription_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    summary_model: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="approved")
    consent_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    review_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    audio_retained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_email: Mapped[str] = mapped_column(String(255), nullable=False)
