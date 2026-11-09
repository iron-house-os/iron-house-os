from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.estimate import EstimateCreate


class ValidationSeverity(StrEnum):
    error = "error"
    warning = "warning"
    info = "info"


class EstimateValidationIssue(BaseModel):
    severity: ValidationSeverity
    code: str
    message: str
    line_item_index: int | None = None
    field: str | None = None


class EstimateValidationResult(BaseModel):
    is_valid: bool
    errors: int
    warnings: int
    issues: list[EstimateValidationIssue] = Field(default_factory=list)


class EstimateValidationRequest(BaseModel):
    estimate: EstimateCreate
    require_cost_codes: bool = True
    require_priced_items: bool = True
    minimum_profit_percent: float = Field(default=5, ge=0)
