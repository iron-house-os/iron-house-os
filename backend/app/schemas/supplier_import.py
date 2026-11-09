from pydantic import BaseModel, Field

from app.schemas.supplier import SupplierCreate, SupplierList


class SupplierImportRow(BaseModel):
    company: str | None = None
    category: str | None = None
    secondary_categories: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    branch_location: str | None = None
    region: str | None = None
    address: str | None = None
    status: str | None = None
    source: str | None = None
    source_url: str | None = None
    notes: str | None = None
    preferred: bool | None = None


class SupplierImportPreviewItem(BaseModel):
    row_number: int
    valid: bool
    supplier: SupplierCreate | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SupplierImportPreviewRequest(BaseModel):
    rows: list[SupplierImportRow]


class SupplierImportPreviewResponse(BaseModel):
    items: list[SupplierImportPreviewItem]
    valid_count: int
    error_count: int
    warning_count: int


class SupplierImportCommitRequest(SupplierImportPreviewRequest):
    skip_invalid: bool = True


class SupplierImportCommitResponse(BaseModel):
    created: SupplierList
    skipped_rows: list[SupplierImportPreviewItem] = Field(default_factory=list)
    warning_rows: list[SupplierImportPreviewItem] = Field(default_factory=list)
