from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

WorkflowType = Literal[
    "customer_quote",
    "estimate",
    "purchase_order_request",
    "supplier_quote_comparison",
]
DraftPayload = Annotated[dict, Field(max_length=250)]


class WorkflowDraftCreate(BaseModel):
    workflow_type: WorkflowType
    title: str = Field(min_length=1, max_length=255)
    payload: DraftPayload = Field(default_factory=dict)
    project_id: UUID | None = None
    schema_version: int = Field(default=1, ge=1, le=100)


class WorkflowDraftUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    payload: DraftPayload | None = None
    project_id: UUID | None = None
    schema_version: int | None = Field(default=None, ge=1, le=100)


class WorkflowDraftTransition(BaseModel):
    expected_revision: int = Field(ge=1)


class WorkflowDraftRead(BaseModel):
    id: UUID
    owner_account_id: UUID
    project_id: UUID | None
    workflow_type: WorkflowType
    title: str
    payload: dict
    schema_version: int
    revision: int
    status: Literal["active", "cancelled", "completed"]
    last_saved_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowDraftList(BaseModel):
    items: list[WorkflowDraftRead]
    total: int
