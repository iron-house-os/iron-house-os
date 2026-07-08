from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.rfq_automation import RFQAutomationInputItem, RFQScopeRecommendation


class RFQLinkageRequest(BaseModel):
    project_id: UUID | None = None
    project_name: str | None = None
    municipality: str | None = None
    source_items: list[RFQAutomationInputItem] = Field(default_factory=list)
    include_default_civil_scopes: bool = True


class RFQPackageDraft(BaseModel):
    title: str
    scope_summary: str
    supplier_category_targets: list[str]
    required_documents: list[str]
    source_scope: str
    priority: int
    review_notes: list[str]


class RFQLinkageResponse(BaseModel):
    project_id: UUID | None
    project_name: str | None
    package_count: int
    packages: list[RFQPackageDraft]
    warnings: list[str]
    recommendations: list[RFQScopeRecommendation]
