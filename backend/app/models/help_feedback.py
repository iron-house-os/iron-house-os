from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class HelpImprovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "help_improvements"
    __table_args__ = (UniqueConstraint("group_key"),)

    group_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    route: Mapped[str] = mapped_column(String(300), nullable=False, default="", index=True)
    source_ids_json: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new", index=True)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    latest_note: Mapped[str | None] = mapped_column(Text)
    latest_project_name: Mapped[str | None] = mapped_column(String(160))
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HelpFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "help_feedback"

    improvement_id: Mapped[UUID] = mapped_column(
        ForeignKey("help_improvements.id"), nullable=False, index=True
    )
    audience: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    project_name: Mapped[str | None] = mapped_column(String(160))
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
