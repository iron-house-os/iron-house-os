from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


FinancialEntryType = Literal["budget", "commitment", "actual", "revenue", "forecast_adjustment"]
FinancialCategory = Literal["labour", "equipment", "material", "trucking", "subcontract", "rental", "fuel", "overhead", "contingency", "bonding", "insurance", "other"]


class FinancialEntryCreate(BaseModel):
    project_id: UUID
    cost_code: str = Field(min_length=1, max_length=32)
    entry_type: FinancialEntryType
    category: FinancialCategory
    amount: float = Field(gt=0, le=999_999_999)
    entry_date: date
    vendor_name: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=120)
    description: str | None = None
    status: Literal["draft", "open", "posted", "closed", "void"] = "posted"
    metadata_json: dict = Field(default_factory=dict)


class FinancialEntryRead(FinancialEntryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_type: str
    source_id: UUID | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class CostCodeFinancialSummary(BaseModel):
    cost_code: str
    budget: float
    committed: float
    actual: float
    forecast: float
    variance: float


class ProjectFinancialSummary(BaseModel):
    project_id: UUID
    project_name: str
    contract_value: float
    budget: float
    committed: float
    actual: float
    forecast_cost: float
    cost_variance: float
    forecast_profit: float
    forecast_margin_percent: float
    entries: list[FinancialEntryRead]
    cost_codes: list[CostCodeFinancialSummary]


class EstimateBudgetImportRequest(BaseModel):
    workspace_id: UUID | None = None
