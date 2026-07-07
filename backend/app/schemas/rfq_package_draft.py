from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RFQPackageDraftSupplier(BaseModel):
    supplier_name: str = Field(min_length=1)
    category: str | None = None
    recipient_email: EmailStr | None = None


class RFQPackageDraftRequest(BaseModel):
    project_name: str = Field(min_length=1)
    project_location: str | None = None
    owner: str | None = None
    tender_close: datetime | None = None
    quote_return_deadline: datetime | None = None
    scope_summary: str = Field(min_length=1)
    scope_items: list[str] = Field(default_factory=list)
    attachment_names: list[str] = Field(default_factory=list)
    suppliers: list[RFQPackageDraftSupplier] = Field(default_factory=list)
    sender_name: str = "Iron House"
    sender_phone: str | None = None
    sender_email: EmailStr | None = None


class RFQPackageDraftEmail(BaseModel):
    supplier_name: str
    category: str | None = None
    recipient_email: EmailStr | None = None
    subject: str
    body: str
    attachment_names: list[str]


class RFQPackageDraftResponse(BaseModel):
    package_summary: str
    drafts: list[RFQPackageDraftEmail]
    supplier_count: int
    attachment_count: int
