from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_drafts"

    owner_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_accounts.id"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
    )
    workflow_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    last_saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
