from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document import (
    DocumentCategory,
    DocumentCreate,
    DocumentIntegrity,
    DocumentList,
    DocumentRead,
    DocumentUpdate,
    DocumentUpdateStatus,
    DocumentUploadResponse,
    RFQAttachmentManifest,
    RFQAttachmentManifestRequest,
)
from app.services import documents

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]
OptionalQuery = Annotated[str | None, Query()]
OptionalUUIDQuery = Annotated[UUID | None, Query()]


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: DBSession) -> DocumentRead:
    return documents.create_document(db, payload)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    db: DBSession,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    category: DocumentCategory = Form(default=DocumentCategory.other),
    project_id: UUID | None = Form(default=None),
    description: str | None = Form(default=None),
    revision: str | None = Form(default=None),
) -> DocumentUploadResponse:
    return await documents.upload_document(
        db,
        file=file,
        title=title,
        category=category.value,
        project_id=project_id,
        description=description,
        revision=revision,
    )


@router.get("", response_model=DocumentList)
def list_documents(
    db: DBSession,
    category: OptionalQuery = None,
    status: OptionalQuery = None,
    project_id: OptionalUUIDQuery = None,
    rfq_package_id: OptionalUUIDQuery = None,
    tender_id: OptionalUUIDQuery = None,
) -> DocumentList:
    return documents.list_documents(
        db,
        category=category,
        status=status,
        project_id=project_id,
        rfq_package_id=rfq_package_id,
        tender_id=tender_id,
    )


@router.post("/attachment-manifest", response_model=RFQAttachmentManifest)
def attachment_manifest(payload: RFQAttachmentManifestRequest, db: DBSession) -> RFQAttachmentManifest:
    return documents.build_attachment_manifest(db, payload.document_ids)


@router.get("/{document_id}", response_model=DocumentRead)
def read_document(document_id: UUID, db: DBSession) -> DocumentRead:
    return documents.get_document(db, document_id)


@router.get("/{document_id}/download")
def download_document(document_id: UUID, db: DBSession) -> FileResponse:
    document = documents.get_document(db, document_id)
    path = documents.get_document_file_path(db, document_id)
    filename = document.metadata.get("original_filename") or document.title
    return FileResponse(path, filename=filename)


@router.get("/{document_id}/integrity", response_model=DocumentIntegrity)
def document_integrity(document_id: UUID, db: DBSession) -> DocumentIntegrity:
    return documents.document_integrity(db, document_id)


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
