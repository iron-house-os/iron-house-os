from typing import Literal

from pydantic import BaseModel, Field

ProcurementScope = Literal[
    "pipe_supply",
    "structures_supply",
    "aggregate_supply",
    "asphalt_paving",
    "concrete_subcontract",
    "testing",
    "traffic_control",
    "landscaping",
    "earthworks_support",
    "disposal",
    "misc",
]

SourceSignal = Literal["quantity", "municipality", "estimate", "manual"]


class RFQAutomationInputItem(BaseModel):
    category: str
    description: str
    quantity: float | None = None
    unit: str | None = None
    source: SourceSignal = "manual"


class RFQAutomationRequest(BaseModel):
    project_name: str | None = None
    municipality: str | None = None
    items: list[RFQAutomationInputItem] = Field(default_factory=list)
    include_default_civil_scopes: bool = True


class RFQScopeRecommendation(BaseModel):
    scope: ProcurementScope
    title: str
    reason: str
    supplier_categories: list[str]
    required_documents: list[str]
    priority: int
    source_signals: list[SourceSignal]
    review_notes: list[str]


class RFQAutomationResponse(BaseModel):
    project_name: str | None
    municipality: str | None
    recommendation_count: int
    high_priority_count: int
    recommendations: list[RFQScopeRecommendation]
    warnings: list[str]
