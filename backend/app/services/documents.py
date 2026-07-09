from hashlib import sha256
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.document import Document
from app.schemas.document import (
    DocumentCategory,
    DocumentCreate,
    DocumentIntegrity,
    DocumentList,
    DocumentRead,
    DocumentStatus,
    DocumentUpdate,
    DocumentUpdateStatus,
    DocumentUploadResponse,
    DrawingMetadata,
    RFQAttachmentManifest,
    RFQAttachmentManifestItem,
)
from app.services.file_storage import resolve_storage_path, store_upload


async def upload_document(
    db: Session,
    file: UploadFile,
    title: str | None,
    category: str,
    project_id: UUID | None = None,
    description: str | None = None,
    revision: str | None = None,
) -> DocumentUploadResponse:
    stored = await store_upload(file, project_id=str(project_id) if project_id else None)
    duplicates = _duplicate_document_ids(db, stored.sha256_hash)
    metadata = {
        "original_filename": stored.original_filename,
        "safe_filename": stored.safe_filename,
        "extension": stored.extension,
        "content_type": stored.content_type,
        "size_bytes": stored.size_bytes,
        "sha256_hash": stored.sha256_hash,
    }
    drawing = None
    if category == DocumentCategory.drawing.value:
        drawing = DrawingMetadata(revision=revision, storage_uri=stored.storage_uri)

    payload = DocumentCreate(
        title=title or stored.original_filename,
        category=DocumentCategory(category),
        status=DocumentStatus.registered,
        project_id=project_id,
        storage_uri=stored.storage_uri,
        description=description,
        drawing=drawing,
        metadata=metadata,
    )
    document = create_document(db, payload)
    return DocumentUploadResponse(
        document=document,
        original_filename=stored.original_filename,
        safe_filename=stored.safe_filename,
        extension=stored.extension,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        sha256_hash=stored.sha256_hash,
        duplicate_document_ids=duplicates,
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


def get_document_file_path(db: Session, document_id: UUID) -> Path:
    document = _load_document(db, document_id)
    if not document.storage_uri:
        raise AppError("Document has no stored file", status_code=404)
    return resolve_storage_path(document.storage_uri)


def document_integrity(db: Session, document_id: UUID) -> DocumentIntegrity:
    document = _load_document(db, document_id)
    metadata = document.metadata_json or {}
    file_exists = False
    current_hash = None
    size_bytes = None
    if document.storage_uri:
        try:
            path = resolve_storage_path(document.storage_uri)
            file_exists = True
            digest = sha256()
            size = 0
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    digest.update(chunk)
            current_hash = digest.hexdigest()
            size_bytes = size
        except AppError:
            file_exists = False
    duplicate_ids = _duplicate_document_ids(
        db,
        metadata.get("sha256_hash"),
        exclude_id=document.id,
    )
    return DocumentIntegrity(
        document_id=document.id,
        storage_uri=document.storage_uri,
        file_exists=file_exists,
        sha256_hash=current_hash,
        size_bytes=size_bytes,
        duplicate_document_ids=duplicate_ids,
    )


def build_attachment_manifest(db: Session, document_ids: list[UUID]) -> RFQAttachmentManifest:
    items: list[RFQAttachmentManifestItem] = []
    warnings: list[str] = []
    total_size = 0
    for document_id in document_ids:
        document = _load_document(db, document_id)
        metadata = document.metadata_json or {}
        size = metadata.get("size_bytes")
        if isinstance(size, int):
            total_size += size
        if document.status in {"superseded", "archived"}:
            warnings.append(f"{document.title} is {document.status}.")
        if not document.storage_uri:
            warnings.append(f"{document.title} has no stored file.")
        items.append(
            RFQAttachmentManifestItem(
                document_id=document.id,
                title=document.title,
                category=document.category,
                status=DocumentStatus(document.status),
                storage_uri=document.storage_uri,
                filename=metadata.get("original_filename"),
                size_bytes=size if isinstance(size, int) else None,
                sha256_hash=metadata.get("sha256_hash"),
            )
        )
    return RFQAttachmentManifest(
        item_count=len(items),
        total_size_bytes=total_size,
        items=items,
        warnings=warnings,
    )


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


def _duplicate_document_ids(
    db: Session,
    sha256_hash: str | None,
    exclude_id: UUID | None = None,
) -> list[UUID]:
    if not sha256_hash:
        return []
    rows = db.scalars(select(Document)).all()
    duplicate_ids: list[UUID] = []
    for row in rows:
        if exclude_id and row.id == exclude_id:
            continue
        metadata = row.metadata_json or {}
        if metadata.get("sha256_hash") == sha256_hash:
            duplicate_ids.append(row.id)
    return duplicate_ids


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