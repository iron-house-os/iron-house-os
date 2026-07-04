from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Bid(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bids"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tender_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenders.id"))
    status: Mapped[str] = mapped_column(String(80), default="draft")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    summary: Mapped[str | None] = mapped_column(Text)
    bid_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    project = relationship("Project", back_populates="bids")
    tender = relationship("Tender", back_populates="bids")
