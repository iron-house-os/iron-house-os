from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document import (
    DocumentCreate,
    DocumentList,
    DocumentRead,
    DocumentUpdate,
    DocumentUpdateStatus,
)
from app.services import documents

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]
OptionalQuery = Annotated[str | None, Query()]
OptionalUUIDQuery = Annotated[UUID | None, Query()]


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: DBSession) -> DocumentRead:
    return documents.create_document(db, payload)


@router.get("", response_model=DocumentList)
def list_documents(
    db: DBSession,
    category: OptionalQuery = None,
    status: OptionalQuery = None,
    project_id: OptionalUUIDQuery = None,
    rfq_package_id: OptionalUUIDQuery = None,
) -> DocumentList:
    return documents.list_documents(
        db,
        category=category,
        status=status,
        project_id=project_id,
        rfq_package_id=rfq_package_id,
    )


@router.get("/{document_id}", response_model=DocumentRead)
def read_document(document_id: UUID, db: DBSession) -> DocumentRead:
    return documents.get_document(db, document_id)


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: UUID,
    payload: DocumentUpdate,
    db: DBSession,
) -> DocumentRead:
    return documents.update_document(db, document_id, payload)


@router.patch("/{document_id}/status", response_model=DocumentRead)
def update_document_status(
    document_id: UUID,
    payload: DocumentUpdateStatus,
    db: DBSession,
) -> DocumentRead:
    return documents.update_document_status(db, document_id, payload)
