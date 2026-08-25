from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.finance import CustomerInvoiceCreate, CustomerInvoiceRead
from app.schemas.project import ProjectStatus


class ChatInvoiceIntakeRecord(BaseModel):
    invoice: CustomerInvoiceCreate
    create_project_if_missing: bool = True
    project_status: ProjectStatus = ProjectStatus.construction


class ChatInvoiceIntakeRequest(BaseModel):
    items: list[ChatInvoiceIntakeRecord] = Field(min_length=1, max_length=50)


ChatInvoiceIntakeStatus = Literal["created", "reused", "conflict", "error"]


class ChatInvoiceIntakeItemResult(BaseModel):
    invoice_number: str
    status: ChatInvoiceIntakeStatus
    project_id: UUID | None = None
    project_created: bool = False
    invoice: CustomerInvoiceRead | None = None
    detail: str | None = None


class ChatInvoiceIntakeResponse(BaseModel):
    items: list[ChatInvoiceIntakeItemResult]
    created_count: int
    reused_count: int
    conflict_count: int
    error_count: int
