from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(80), default="registered", index=True)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"))
    rfq_package_id: Mapped[UUID | None] = mapped_column(ForeignKey("rfq_packages.id"))
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"))
    storage_uri: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    sheet_number: Mapped[str | None] = mapped_column(String(80))
    drawing_title: Mapped[str | None] = mapped_column(String(255))
    discipline: Mapped[str | None] = mapped_column(String(120))
    revision: Mapped[str | None] = mapped_column(String(80))
    issue_date: Mapped[date | None] = mapped_column(Date)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)


class Drawing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drawings"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    discipline: Mapped[str | None] = mapped_column(String(120))
    revision: Mapped[str | None] = mapped_column(String(80))
    storage_uri: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    project = relationship("Project", back_populates="drawings")


class Takeoff(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "takeoffs"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    drawing_id: Mapped[UUID | None] = mapped_column(ForeignKey("drawings.id"))
    status: Mapped[str] = mapped_column(String(80), default="pending")
    notes: Mapped[str | None] = mapped_column(Text)
    quantities_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    project = relationship("Project", back_populates="takeoffs")
