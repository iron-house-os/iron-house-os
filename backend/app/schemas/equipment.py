from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


EquipmentStatus = Literal["available", "reserved", "in_use", "maintenance", "retired"]


class EquipmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    equipment_type: str | None = Field(default=None, max_length=120)
    identifier: str | None = Field(default=None, max_length=120)
    status: EquipmentStatus = "available"
    hourly_rate: float | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Equipment name is required.")
        return normalized

    @field_validator("equipment_type", "identifier")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        normalized = (value or "").strip()
        return normalized or None


class EquipmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    equipment_type: str | None = Field(default=None, max_length=120)
    identifier: str | None = Field(default=None, max_length=120)
    status: EquipmentStatus | None = None
    hourly_rate: float | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Equipment name cannot be blank.")
        return normalized

    @field_validator("equipment_type", "identifier")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        normalized = (value or "").strip()
        return normalized or None


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    equipment_type: str | None
    identifier: str | None
    status: EquipmentStatus
    hourly_rate: float | None
    created_at: datetime
    updated_at: datetime


class EquipmentList(BaseModel):
    items: list[EquipmentRead]
    total: int
