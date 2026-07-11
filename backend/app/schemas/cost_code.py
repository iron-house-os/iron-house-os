from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.estimate import EstimateItemType, EstimateUnit


class CostCodeGroup(StrEnum):
    general = "general"
    earthworks = "earthworks"
    utilities = "utilities"
    structures = "structures"
    concrete = "concrete"
    asphalt = "asphalt"
    traffic = "traffic"
    landscaping = "landscaping"
    testing = "testing"
    closeout = "closeout"


class CostCode(BaseModel):
    code: str = Field(min_length=3, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    group: CostCodeGroup
    default_item_type: EstimateItemType
    default_unit: EstimateUnit
    description: str | None = None
    active: bool = True
    parent_code: str | None = None
    tags: list[str] = Field(default_factory=list)


class CostCodeLibrary(BaseModel):
    version: str
    items: list[CostCode]


class CostCodeResolveRequest(BaseModel):
    code: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def require_code_or_description(self) -> "CostCodeResolveRequest":
        if not self.code and not self.description:
            raise ValueError("code or description is required")
        return self


class CostCodeResolveResponse(BaseModel):
    match: CostCode | None
    confidence: float = Field(ge=0, le=1)
    alternatives: list[CostCode] = Field(default_factory=list)
