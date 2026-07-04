from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Drawing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drawings"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    discipline: Mapped[str | None] = mapped_column(String(120))
    revision: Mapped[str | None] = mapped_column(String(80))
    storage_uri: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    project = relationship("Project", back_populates="drawings")


class Takeoff(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "takeoffs"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    drawing_id: Mapped[UUID | None] = mapped_column(ForeignKey("drawings.id"))
    status: Mapped[str] = mapped_column(String(80), default="pending")
    notes: Mapped[str | None] = mapped_column(Text)
    quantities_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    project = relationship("Project", back_populates="takeoffs")
