from pydantic import BaseModel, Field

from app.schemas.supplier import SupplierRead


class SupplierRFQCandidateRequest(BaseModel):
    category: str = Field(min_length=1)
    service_area: str | None = None
    include_needs_verification: bool = False
    include_no_account: bool = False
    limit: int = Field(default=25, ge=1, le=100)


class SupplierRFQCandidate(BaseModel):
    supplier: SupplierRead
    selected_email: str | None = None
    preferred: bool = False
    status: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SupplierRFQCandidateList(BaseModel):
    items: list[SupplierRFQCandidate]
    total: int
