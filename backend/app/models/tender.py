from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Tender(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenders"

    municipality_id: Mapped[UUID | None] = mapped_column(ForeignKey("municipalities.id"))
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"))
    rfq_package_id: Mapped[UUID | None] = mapped_column(ForeignKey("rfq_packages.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tender_number: Mapped[str | None] = mapped_column(String(120), unique=True)
    source: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(String(500))
    owner: Mapped[str | None] = mapped_column(String(255))
    municipality_name: Mapped[str | None] = mapped_column("municipality", String(255))
    closing_date: Mapped[date | None] = mapped_column(Date)
    site_meeting_date: Mapped[date | None] = mapped_column(Date)
    question_deadline: Mapped[date | None] = mapped_column(Date)
    project_address: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="new")
    estimated_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    municipality = relationship("Municipality", back_populates="tenders")
    project = relationship("Project", back_populates="tenders")
    rfq_package = relationship("RFQPackage")
    documents = relationship("Document", back_populates="tender")
    bids = relationship("Bid", back_populates="tender")
