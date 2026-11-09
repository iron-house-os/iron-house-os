from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.supplier import (
    ContactCreate,
    SupplierBulkCreate,
    SupplierCreate,
    SupplierList,
    SupplierRead,
    SupplierUpdate,
)
from app.schemas.supplier_import import (
    SupplierImportCommitRequest,
    SupplierImportCommitResponse,
    SupplierImportPreviewRequest,
    SupplierImportPreviewResponse,
)
from app.schemas.supplier_selection import SupplierRFQCandidateList, SupplierRFQCandidateRequest
from app.services import supplier_import, supplier_selection, suppliers

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, db: DBSession) -> SupplierRead:
    return suppliers.create_supplier(db, payload)


@router.post("/bulk", response_model=SupplierList, status_code=status.HTTP_201_CREATED)
def bulk_create_suppliers(payload: SupplierBulkCreate, db: DBSession) -> SupplierList:
    items = suppliers.bulk_create_suppliers(db, payload.suppliers)
    return SupplierList(items=items, total=len(items))


@router.post("/import-preview", response_model=SupplierImportPreviewResponse)
def preview_supplier_import(payload: SupplierImportPreviewRequest) -> SupplierImportPreviewResponse:
    return supplier_import.preview_supplier_import(payload)


@router.post("/import-commit", response_model=SupplierImportCommitResponse, status_code=status.HTTP_201_CREATED)
def commit_supplier_import(
    payload: SupplierImportCommitRequest,
    db: DBSession,
) -> SupplierImportCommitResponse:
    return supplier_import.commit_supplier_import(db, payload)


@router.get("", response_model=SupplierList)
def list_suppliers(
    db: DBSession,
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    service_area: str | None = Query(default=None),
) -> SupplierList:
    items = suppliers.list_suppliers(
        db,
        search=search,
        category=category,
        service_area=service_area,
    )
    return SupplierList(items=items, total=len(items))


@router.post("/rfq-candidates", response_model=SupplierRFQCandidateList)
def select_rfq_candidates(
    payload: SupplierRFQCandidateRequest,
    db: DBSession,
) -> SupplierRFQCandidateList:
    items = supplier_selection.select_rfq_candidates(db, payload)
    return SupplierRFQCandidateList(items=items, total=len(items))


@router.get("/{supplier_id}", response_model=SupplierRead)
def read_supplier(supplier_id: UUID, db: DBSession) -> SupplierRead:
    return suppliers.get_supplier(db, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(supplier_id: UUID, payload: SupplierUpdate, db: DBSession) -> SupplierRead:
    return suppliers.update_supplier(db, supplier_id, payload)


@router.put("/{supplier_id}/contacts", response_model=SupplierRead)
def replace_supplier_contacts(
    supplier_id: UUID,
    payload: list[ContactCreate],
    db: DBSession,
) -> SupplierRead:
    return suppliers.replace_supplier_contacts(db, supplier_id, payload)
