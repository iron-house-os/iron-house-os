from typing import Literal

from pydantic import BaseModel, Field

QuantityCategory = Literal[
    "pipe",
    "structures",
    "asphalt",
    "concrete",
    "earthworks",
    "landscape",
    "traffic",
    "misc",
]
QuantitySource = Literal["manual", "drawing_intelligence", "ocr", "import", "estimate_override"]
QuantityUnit = Literal["LS", "EA", "m", "m2", "m3", "t", "hr", "day"]


class QuantityItem(BaseModel):
    code: str | None = None
    description: str
    category: QuantityCategory
    quantity: float = Field(ge=0)
    unit: QuantityUnit
    source: QuantitySource = "manual"
    confidence: float = Field(default=1.0, ge=0, le=1)
    estimate_ready: bool = True
    drawing_reference: str | None = None
    notes: str | None = None


class QuantityRegisterRequest(BaseModel):
    project_name: str | None = None
    project_id: str | None = None
    items: list[QuantityItem] = Field(default_factory=list)


class QuantitySummaryLine(BaseModel):
    category: QuantityCategory
    unit: QuantityUnit
    total_quantity: float
    item_count: int
    estimate_ready_count: int


class EstimateReadyItem(BaseModel):
    code: str | None
    description: str
    category: QuantityCategory
    quantity: float
    unit: QuantityUnit
    source: QuantitySource
    confidence: float
    drawing_reference: str | None
    notes: str | None


class QuantityRegisterResponse(BaseModel):
    project_name: str | None
    project_id: str | None
    item_count: int
    estimate_ready_count: int
    low_confidence_count: int
    summaries: list[QuantitySummaryLine]
    estimate_ready_items: list[EstimateReadyItem]
    warnings: list[str]
