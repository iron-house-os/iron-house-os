from uuid import UUID

from fastapi import APIRouter, status

from app.schemas.rfq_package import (
    RFQPackageCreate,
    RFQPackageDocumentCreate,
    RFQPackageList,
    RFQPackageRead,
    RFQPackageReadiness,
    RFQPackageUpdateStatus,
    SupplierRecipientCreate,
)
from app.services.rfq_packages import rfq_package_store

router = APIRouter()


@router.post("", response_model=RFQPackageRead, status_code=status.HTTP_201_CREATED)
def create_rfq_package(payload: RFQPackageCreate) -> RFQPackageRead:
    return rfq_package_store.create(payload)


@router.get("", response_model=RFQPackageList)
def list_rfq_packages() -> RFQPackageList:
    items = rfq_package_store.list()
    return RFQPackageList(items=items, total=len(items))


@router.get("/{rfq_package_id}", response_model=RFQPackageRead)
def read_rfq_package(rfq_package_id: UUID) -> RFQPackageRead:
    return rfq_package_store.get(rfq_package_id)


@router.patch("/{rfq_package_id}/status", response_model=RFQPackageRead)
def update_rfq_package_status(
    rfq_package_id: UUID,
    payload: RFQPackageUpdateStatus,
) -> RFQPackageRead:
    return rfq_package_store.update_status(rfq_package_id, payload)


@router.put("/{rfq_package_id}/suppliers", response_model=RFQPackageRead)
def select_rfq_package_suppliers(
    rfq_package_id: UUID,
    payload: list[SupplierRecipientCreate],
) -> RFQPackageRead:
    return rfq_package_store.select_suppliers(rfq_package_id, payload)


@router.put("/{rfq_package_id}/documents", response_model=RFQPackageRead)
def register_rfq_package_documents(
    rfq_package_id: UUID,
    payload: list[RFQPackageDocumentCreate],
) -> RFQPackageRead:
    return rfq_package_store.register_documents(rfq_package_id, payload)


@router.get("/{rfq_package_id}/readiness", response_model=RFQPackageReadiness)
def read_rfq_package_readiness(rfq_package_id: UUID) -> RFQPackageReadiness:
    return rfq_package_store.readiness(rfq_package_id)
