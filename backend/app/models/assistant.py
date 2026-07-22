from uuid import UUID

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
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
