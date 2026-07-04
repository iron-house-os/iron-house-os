from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.document import Document
from app.schemas.document import (
    DocumentCreate,
    DocumentList,
    DocumentRead,
    DocumentStatus,
    DocumentUpdate,
    DocumentUpdateStatus,
    DrawingMetadata,
)


def create_document(db: Session, payload: DocumentCreate) -> DocumentRead:
    document = Document(**_document_values(payload))
    db.add(document)
    db.commit()
    db.refresh(document)
    return _to_schema(document)


def list_documents(
    db: Session,
    category: str | None = None,
    status: str | None = None,
    project_id: UUID | None = None,
    rfq_package_id: UUID | None = None,
    tender_id: UUID | None = None,
) -> DocumentList:
    statement = select(Document).order_by(Document.created_at.desc())
    if category:
        statement = statement.where(Document.category == category)
    if status:
        statement = statement.where(Document.status == status)
    if project_id:
        statement = statement.where(Document.project_id == project_id)
    if rfq_package_id:
        statement = statement.where(Document.rfq_package_id == rfq_package_id)
    if tender_id:
        statement = statement.where(Document.tender_id == tender_id)
    items = [_to_schema(document) for document in db.scalars(statement).all()]
    return DocumentList(items=items, total=len(items))


def get_document(db: Session, document_id: UUID) -> DocumentRead:
    return _to_schema(_load_document(db, document_id))


def update_document(db: Session, document_id: UUID, payload: DocumentUpdate) -> DocumentRead:
    document = _load_document(db, document_id)
    update_data = payload.model_dump(exclude_unset=True)
    drawing = update_data.pop("drawing", None)
    metadata = update_data.pop("metadata", None)

    for key, value in update_data.items():
        if key == "category" and value is not None:
            value = value.value
        if key == "status" and value is not None:
            value = value.value
        setattr(document, key, value)
    if drawing is not None:
        drawing_metadata = DrawingMetadata(**drawing) if isinstance(drawing, dict) else drawing
        _apply_drawing_metadata(document, drawing_metadata)
    if metadata is not None:
        document.metadata_json = metadata
    db.commit()
    return _to_schema(_load_document(db, document_id))


def update_document_status(
    db: Session,
    document_id: UUID,
    payload: DocumentUpdateStatus,
) -> DocumentRead:
    document = _load_document(db, document_id)
    document.status = payload.status.value
    db.commit()
    return _to_schema(_load_document(db, document_id))


def _load_document(db: Session, document_id: UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise AppError("Document not found", status_code=404)
    return document


def _document_values(payload: DocumentCreate) -> dict:
    values = {
        "title": payload.title,
        "category": payload.category.value,
        "status": payload.status.value,
        "project_id": payload.project_id,
        "rfq_package_id": payload.rfq_package_id,
        "tender_id": payload.tender_id,
        "supplier_id": payload.supplier_id,
        "storage_uri": payload.storage_uri,
        "description": payload.description,
        "metadata_json": payload.metadata,
    }
    if payload.drawing:
        values.update(_drawing_values(payload.drawing))
        if payload.drawing.storage_uri:
            values["storage_uri"] = payload.drawing.storage_uri
    return values


def _apply_drawing_metadata(document: Document, drawing: DrawingMetadata) -> None:
    for key, value in _drawing_values(drawing).items():
        setattr(document, key, value)
    if drawing.storage_uri:
        document.storage_uri = drawing.storage_uri


def _drawing_values(drawing: DrawingMetadata) -> dict:
    return {
        "sheet_number": drawing.sheet_number,
        "drawing_title": drawing.title,
        "discipline": drawing.discipline,
        "revision": drawing.revision,
        "issue_date": drawing.issue_date,
    }


def _to_schema(document: Document) -> DocumentRead:
    drawing = None
    if document.category == "drawing":
        drawing = DrawingMetadata(
            sheet_number=document.sheet_number,
            title=document.drawing_title,
            discipline=document.discipline,
            revision=document.revision,
            issue_date=document.issue_date,
            storage_uri=document.storage_uri,
        )
    return DocumentRead(
        id=document.id,
        title=document.title,
        category=document.category,
        status=DocumentStatus(document.status),
        project_id=document.project_id,
        rfq_package_id=document.rfq_package_id,
        tender_id=document.tender_id,
        supplier_id=document.supplier_id,
        storage_uri=document.storage_uri,
        description=document.description,
        drawing=drawing,
        metadata=document.metadata_json or {},
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
