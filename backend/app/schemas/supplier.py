from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None


class ContactRead(ContactCreate):
    id: UUID


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1)
    category: str | None = None
    service_area: str | None = None
    website: str | None = None
    notes: str | None = None
    metadata: dict = Field(default_factory=dict)
    contacts: list[ContactCreate] = Field(default_factory=list)


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    category: str | None = None
    service_area: str | None = None
    website: str | None = None
    notes: str | None = None
    metadata: dict | None = None


class SupplierRead(BaseModel):
    id: UUID
    name: str
    category: str | None
    service_area: str | None
    website: str | None
    notes: str | None
    metadata: dict
    contacts: list[ContactRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SupplierList(BaseModel):
    items: list[SupplierRead]
    total: int


class SupplierBulkCreate(BaseModel):
    suppliers: list[SupplierCreate]
