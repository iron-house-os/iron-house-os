from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rfq_package import (
    RFQPackageCreate,
    RFQPackageDocumentCreate,
    RFQPackageList,
    RFQPackageRead,
    RFQPackageReadiness,
    RFQPackageUpdateStatus,
    SupplierRecipientCreate,
)
from app.services import rfq_packages

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=RFQPackageRead, status_code=status.HTTP_201_CREATED)
def create_rfq_package(
    payload: RFQPackageCreate,
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.create_rfq_package(db, payload)


@router.get("", response_model=RFQPackageList)
def list_rfq_packages(db: DBSession) -> RFQPackageList:
    items = rfq_packages.list_rfq_packages(db)
    return RFQPackageList(items=items, total=len(items))


@router.get("/{rfq_package_id}", response_model=RFQPackageRead)
def read_rfq_package(
    rfq_package_id: UUID,
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.get_rfq_package(db, rfq_package_id)


@router.patch("/{rfq_package_id}/status", response_model=RFQPackageRead)
def update_rfq_package_status(
    rfq_package_id: UUID,
    payload: RFQPackageUpdateStatus,
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.update_rfq_package_status(db, rfq_package_id, payload)


@router.put("/{rfq_package_id}/suppliers", response_model=RFQPackageRead)
def select_rfq_package_suppliers(
    rfq_package_id: UUID,
    payload: list[SupplierRecipientCreate],
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.select_rfq_package_suppliers(db, rfq_package_id, payload)


@router.put("/{rfq_package_id}/documents", response_model=RFQPackageRead)
def register_rfq_package_documents(
    rfq_package_id: UUID,
    payload: list[RFQPackageDocumentCreate],
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.register_rfq_package_documents(db, rfq_package_id, payload)


@router.get("/{rfq_package_id}/readiness", response_model=RFQPackageReadiness)
def read_rfq_package_readiness(
    rfq_package_id: UUID,
    db: DBSession,
) -> RFQPackageReadiness:
    return rfq_packages.get_rfq_package_readiness(db, rfq_package_id)
