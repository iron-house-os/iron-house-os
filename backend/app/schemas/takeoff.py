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
QuantitySource = Literal["manual", "drawing_intelligence", "ocr", "import", "estimate_override", "takeoff_engine"]
QuantityUnit = Literal["LS", "EA", "m", "m2", "m3", "t", "hr", "day"]
TakeoffMethod = Literal["manual", "scale_measure", "sheet_count", "area_trace", "linear_trace", "allowance", "imported"]
ReadinessStatus = Literal["ready", "review", "blocked"]


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
    takeoff_method: TakeoffMethod = "manual"
    scale: str | None = None
    revision: str | None = None


class DrawingSheetInput(BaseModel):
    sheet_number: str
    title: str
    discipline: str | None = None
    scale: str | None = None
    revision: str | None = None
    notes: str | None = None


class TakeoffExtractionRule(BaseModel):
    category: QuantityCategory
    description: str
    unit: QuantityUnit
    method: TakeoffMethod
    drawing_reference: str | None = None
    measured_value: float = Field(default=0, ge=0)
    multiplier: float = Field(default=1, ge=0)
    waste_factor: float = Field(default=0, ge=0, le=1)
    confidence: float = Field(default=0.75, ge=0, le=1)
    notes: str | None = None


class TakeoffEngineRequest(BaseModel):
    project_name: str | None = None
    project_id: str | None = None
    drawing_set_name: str | None = None
    sheets: list[DrawingSheetInput] = Field(default_factory=list)
    extraction_rules: list[TakeoffExtractionRule] = Field(default_factory=list)
    manual_items: list[QuantityItem] = Field(default_factory=list)


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
    takeoff_method: TakeoffMethod = "manual"
    scale: str | None = None
    revision: str | None = None


class QuantityRegisterResponse(BaseModel):
    project_name: str | None
    project_id: str | None
    item_count: int
    estimate_ready_count: int
    low_confidence_count: int
    summaries: list[QuantitySummaryLine]
    estimate_ready_items: list[EstimateReadyItem]
    warnings: list[str]


class TakeoffReadinessCheck(BaseModel):
    label: str
    status: ReadinessStatus
    detail: str


class TakeoffEngineResponse(BaseModel):
    project_name: str | None
    project_id: str | None
    drawing_set_name: str | None
    sheets_reviewed: int
    generated_items: list[QuantityItem]
    quantity_register: QuantityRegisterResponse
    readiness_checks: list[TakeoffReadinessCheck]
    estimating_handoff_items: list[EstimateReadyItem]
    assumptions: list[str]
    conflicts: list[str]
    next_actions: list[str]
