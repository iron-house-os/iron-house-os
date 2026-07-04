from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_number: Mapped[str | None] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(80), default="planning")
    municipality_id: Mapped[UUID | None] = mapped_column(ForeignKey("municipalities.id"))
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)

    municipality = relationship("Municipality", back_populates="projects")
    rfqs = relationship("RFQ", back_populates="project")
    bids = relationship("Bid", back_populates="project")
    drawings = relationship("Drawing", back_populates="project")
    takeoffs = relationship("Takeoff", back_populates="project")
