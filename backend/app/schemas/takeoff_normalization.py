from pydantic import BaseModel, Field

from app.schemas.takeoff import EstimateReadyItem, QuantityItem


class TakeoffNormalizeRequest(BaseModel):
    project_name: str | None = None
    project_id: str | None = None
    items: list[QuantityItem] = Field(default_factory=list)
    minimum_confidence: float = Field(default=0.7, ge=0, le=1)
    combine_duplicates: bool = True
    require_drawing_reference: bool = True


class TakeoffDuplicateGroup(BaseModel):
    key: str
    item_count: int
    combined_quantity: float
    unit: str
    drawing_references: list[str] = Field(default_factory=list)


class TakeoffNormalizeResponse(BaseModel):
    normalized_items: list[QuantityItem]
    estimate_handoff_items: list[EstimateReadyItem]
    duplicate_groups: list[TakeoffDuplicateGroup]
    rejected_items: list[QuantityItem]
    warnings: list[str]
    input_count: int
    normalized_count: int
    estimate_ready_count: int
