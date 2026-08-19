from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


EquipmentStatus = Literal["available", "reserved", "in_use", "maintenance", "retired"]
CONTROLLED_EQUIPMENT_SAFETY_PROCEDURE_CODES = frozenset(
    {"SWP-001", "SWP-002", "SWP-003", "SWP-004", "SWP-007", "SWP-008"}
)


def _normalize_safety_procedure_codes(values: list[str]) -> list[str]:
    normalized = list(dict.fromkeys(value.strip().upper() for value in values if value.strip()))
    unknown = sorted(set(normalized) - CONTROLLED_EQUIPMENT_SAFETY_PROCEDURE_CODES)
    if unknown:
        raise ValueError(f"Unknown or uncontrolled safety procedure code: {', '.join(unknown)}")
    return normalized


class EquipmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    equipment_type: str | None = Field(default=None, max_length=120)
    identifier: str | None = Field(default=None, max_length=120)
    status: EquipmentStatus = "available"
    hourly_rate: float | None = Field(default=None, ge=0)
    safety_procedure_codes: list[str] = Field(default_factory=list, max_length=12)

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

    @field_validator("safety_procedure_codes")
    @classmethod
    def normalize_safety_procedure_codes(cls, values: list[str]) -> list[str]:
        return _normalize_safety_procedure_codes(values)


class EquipmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    equipment_type: str | None = Field(default=None, max_length=120)
    identifier: str | None = Field(default=None, max_length=120)
    status: EquipmentStatus | None = None
    hourly_rate: float | None = Field(default=None, ge=0)
    safety_procedure_codes: list[str] | None = Field(default=None, max_length=12)

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

    @field_validator("safety_procedure_codes")
    @classmethod
    def normalize_safety_procedure_codes(cls, values: list[str] | None) -> list[str] | None:
        return _normalize_safety_procedure_codes(values) if values is not None else None


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    equipment_type: str | None
    identifier: str | None
    status: EquipmentStatus
    hourly_rate: float | None
    safety_procedure_codes: list[str]
    created_at: datetime
    updated_at: datetime


class EquipmentList(BaseModel):
    items: list[EquipmentRead]
    total: int
