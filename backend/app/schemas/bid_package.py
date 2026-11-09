from typing import Literal

from pydantic import BaseModel, Field

BidPackageSection = Literal[
    "executive_summary",
    "scope_of_work",
    "assumptions",
    "exclusions",
    "risks",
    "municipality_requirements",
    "quantities",
    "rfq_status",
    "supplier_coverage",
    "documents",
]
ReadinessStatus = Literal["ready", "needs_review", "missing"]


class BidPackageInputItem(BaseModel):
    section: BidPackageSection
    title: str
    status: ReadinessStatus = "needs_review"
    content: str | None = None
    source: str = "manual"


class BidPackageGenerateRequest(BaseModel):
    project_name: str
    municipality: str | None = None
    bid_due_date: str | None = None
    estimated_price: float | None = None
    items: list[BidPackageInputItem] = Field(default_factory=list)


class BidPackageChecklistItem(BaseModel):
    section: BidPackageSection
    title: str
    status: ReadinessStatus
    note: str


class BidPackageSummary(BaseModel):
    project_name: str
    municipality: str | None
    bid_due_date: str | None
    estimated_price: float | None
    readiness_score: int
    ready_count: int
    needs_review_count: int
    missing_count: int


class BidPackageGenerateResponse(BaseModel):
    summary: BidPackageSummary
    executive_summary: str
    scope_of_work: list[str]
    assumptions: list[str]
    exclusions: list[str]
    risks: list[str]
    checklist: list[BidPackageChecklistItem]
    missing_items: list[str]
    warnings: list[str]
