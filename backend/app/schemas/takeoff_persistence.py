from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.takeoff import QuantityItem, QuantityRegisterResponse, TakeoffEngineResponse


class TakeoffSaveRequest(BaseModel):
    project_id: UUID
    drawing_id: UUID | None = None
    status: str = Field(default="draft", min_length=1)
    notes: str | None = None
    items: list[QuantityItem] = Field(default_factory=list)
    engine_result: TakeoffEngineResponse | None = None
    quantity_register: QuantityRegisterResponse | None = None


class TakeoffRead(BaseModel):
    id: UUID
    project_id: UUID
    drawing_id: UUID | None
    status: str
    notes: str | None
    quantities: dict
    created_at: datetime
    updated_at: datetime


class TakeoffList(BaseModel):
    items: list[TakeoffRead]
    total: int
