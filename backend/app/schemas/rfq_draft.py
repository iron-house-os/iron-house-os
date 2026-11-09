from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RFQDraftRequest(BaseModel):
    project_name: str = Field(min_length=1)
    project_location: str | None = None
    owner: str | None = None
    tender_close: datetime | None = None
    quote_return_deadline: datetime | None = None
    category: str = Field(min_length=1)
    supplier_name: str = Field(min_length=1)
    recipient_email: EmailStr | None = None
    scope_items: list[str] = Field(default_factory=list)
    attachment_names: list[str] = Field(default_factory=list)
    sender_name: str = "Iron House"
    sender_phone: str | None = None
    sender_email: EmailStr | None = None


class RFQDraftResponse(BaseModel):
    subject: str
    body: str
    recipient_email: EmailStr | None = None
    attachment_names: list[str]
