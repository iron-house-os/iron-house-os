from typing import Literal

from pydantic import BaseModel, Field

RequirementCategory = Literal[
    "approved_materials",
    "testing",
    "compaction",
    "restoration",
    "traffic_control",
    "esc",
    "permits",
    "inspections",
    "documentation",
]
CostImpact = Literal["low", "medium", "high"]
ProjectScope = Literal["water", "sanitary", "storm", "roadworks", "asphalt", "concrete", "traffic", "landscape", "earthworks"]


class MunicipalityCheckRequest(BaseModel):
    municipality: str
    project_scopes: list[ProjectScope] = Field(default_factory=list)


class MunicipalityRequirement(BaseModel):
    municipality: str
    category: RequirementCategory
    title: str
    description: str
    scopes: list[ProjectScope]
    cost_impact: CostImpact
    estimating_note: str
    rfq_note: str | None = None


class MunicipalityCheckResponse(BaseModel):
    municipality: str
    project_scopes: list[ProjectScope]
    requirement_count: int
    high_impact_count: int
    requirements: list[MunicipalityRequirement]
    warnings: list[str]
