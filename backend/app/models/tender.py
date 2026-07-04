from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Tender(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenders"

    municipality_id: Mapped[UUID | None] = mapped_column(ForeignKey("municipalities.id"))
    source: Mapped[str | None] = mapped_column(String(120))
    reference_number: Mapped[str | None] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="watching")
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)

    municipality = relationship("Municipality", back_populates="tenders")
    bids = relationship("Bid", back_populates="tender")
