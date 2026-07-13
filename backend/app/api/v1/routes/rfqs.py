from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rfq_draft import RFQDraftRequest, RFQDraftResponse
from app.schemas.rfq_package import (
    RFQPackageBuildResponse,
    RFQPackageCreate,
    RFQPackageDocumentCreate,
    RFQPackageDocumentStatusUpdate,
    RFQPackageList,
    RFQPackageRead,
    RFQPackageReadiness,
    RFQPackageUpdateStatus,
    RFQScopeGenerationRequest,
    SupplierRecipientCreate,
    SupplierRecipientStatusUpdate,
)
from app.schemas.rfq_workflow import (
    RFQCommunicationWorkflow,
    RFQWorkflowPrepareRequest,
    SupplierResponseCreate,
)
from app.services import rfq_drafts, rfq_packages, rfq_workflows

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


@router.post("/draft", response_model=RFQDraftResponse)
def build_rfq_draft(payload: RFQDraftRequest) -> RFQDraftResponse:
    return rfq_drafts.build_rfq_draft(payload)


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


@router.post("/{rfq_package_id}/supplier-scopes", response_model=RFQPackageRead)
def generate_rfq_supplier_scopes(
    rfq_package_id: UUID,
    payload: RFQScopeGenerationRequest,
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.generate_rfq_supplier_scopes(db, rfq_package_id, payload)


@router.patch(
    "/{rfq_package_id}/suppliers/{recipient_id}/status",
    response_model=RFQPackageRead,
)
def update_rfq_recipient_status(
    rfq_package_id: UUID,
    recipient_id: UUID,
    payload: SupplierRecipientStatusUpdate,
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.update_rfq_recipient_status(
        db,
        rfq_package_id,
        recipient_id,
        payload,
    )


@router.put("/{rfq_package_id}/documents", response_model=RFQPackageRead)
def register_rfq_package_documents(
    rfq_package_id: UUID,
    payload: list[RFQPackageDocumentCreate],
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.register_rfq_package_documents(db, rfq_package_id, payload)


@router.patch(
    "/{rfq_package_id}/documents/{document_id}/status",
    response_model=RFQPackageRead,
)
def update_rfq_document_status(
    rfq_package_id: UUID,
    document_id: UUID,
    payload: RFQPackageDocumentStatusUpdate,
    db: DBSession,
) -> RFQPackageRead:
    return rfq_packages.update_rfq_document_status(
        db,
        rfq_package_id,
        document_id,
        payload,
    )


@router.get("/{rfq_package_id}/readiness", response_model=RFQPackageReadiness)
def read_rfq_package_readiness(
    rfq_package_id: UUID,
    db: DBSession,
) -> RFQPackageReadiness:
    return rfq_packages.get_rfq_package_readiness(db, rfq_package_id)


@router.post("/{rfq_package_id}/build", response_model=RFQPackageBuildResponse)
def build_rfq_supplier_packages(
    rfq_package_id: UUID,
    db: DBSession,
) -> RFQPackageBuildResponse:
    return rfq_packages.build_rfq_supplier_packages(db, rfq_package_id)


@router.get(
    "/{rfq_package_id}/communication-workflow",
    response_model=RFQCommunicationWorkflow,
)
def read_rfq_communication_workflow(
    rfq_package_id: UUID,
    db: DBSession,
) -> RFQCommunicationWorkflow:
    return rfq_workflows.get_rfq_communication_workflow(db, rfq_package_id)


@router.post(
    "/{rfq_package_id}/communication-workflow/prepare",
    response_model=RFQCommunicationWorkflow,
)
def prepare_rfq_communication_workflow(
    rfq_package_id: UUID,
    payload: RFQWorkflowPrepareRequest,
    db: DBSession,
) -> RFQCommunicationWorkflow:
    return rfq_workflows.prepare_rfq_communication_workflow(
        db,
        rfq_package_id,
        payload,
    )


@router.post(
    "/{rfq_package_id}/supplier-responses",
    response_model=RFQCommunicationWorkflow,
    status_code=status.HTTP_201_CREATED,
)
def record_supplier_response(
    rfq_package_id: UUID,
    payload: SupplierResponseCreate,
    db: DBSession,
) -> RFQCommunicationWorkflow:
    return rfq_workflows.record_supplier_response(db, rfq_package_id, payload)
