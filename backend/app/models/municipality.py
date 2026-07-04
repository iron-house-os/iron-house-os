from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Municipality(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "municipalities"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    region: Mapped[str | None] = mapped_column(String(120))
    standards_uri: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    standards_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    projects = relationship("Project", back_populates="municipality")
    tenders = relationship("Tender", back_populates="municipality")
