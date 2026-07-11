from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
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
from app.services.document_audit import (
    DocumentAuditEvent,
    emit_document_audit_event,
    export_document_audit_events_csv,
    list_recent_document_audit_events,
    summarize_document_audit_events,
)
from app.services.request_context import get_request_audit_context
from app.services.signed_download import DEFAULT_TTL_SECONDS, create_download_token, verify_download_token

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]
OptionalQuery = Annotated[str | None, Query()]
OptionalUUIDQuery = Annotated[UUID | None, Query()]


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: DBSession) -> DocumentRead:
    return documents.create_document(db, payload)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    db: DBSession,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    category: DocumentCategory = Form(default=DocumentCategory.other),
    project_id: UUID | None = Form(default=None),
    description: str | None = Form(default=None),
    revision: str | None = Form(default=None),
) -> DocumentUploadResponse:
    response = await documents.upload_document(
        db,
        file=file,
        title=title,
        category=category.value,
        project_id=project_id,
        description=description,
        revision=revision,
    )
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="upload",
            document_id=response.document.id,
            project_id=project_id,
            actor=context.actor,
            request_id=context.request_id,
            metadata={"filename": response.original_filename, "size_bytes": response.size_bytes},
        )
    )
    return response


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


@router.get("/audit-events")
def document_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    items = list_recent_document_audit_events(
        limit,
        action=action,
        outcome=outcome,
        actor=actor,
        project_id=project_id,
    )
    return {"items": items, "total": len(items)}


@router.get("/audit-events/summary")
def document_audit_summary() -> dict[str, Any]:
    return summarize_document_audit_events()


@router.get("/audit-events/export.csv")
def document_audit_export(
    limit: int = Query(default=200, ge=1, le=200),
    action: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> Response:
    events = list_recent_document_audit_events(
        limit,
        action=action,
        outcome=outcome,
        actor=actor,
        project_id=project_id,
    )
    csv_text = export_document_audit_events_csv(events)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=document-audit-events.csv"},
    )


@router.post("/attachment-manifest", response_model=RFQAttachmentManifest)
def attachment_manifest(payload: RFQAttachmentManifestRequest, db: DBSession) -> RFQAttachmentManifest:
    return documents.build_attachment_manifest(db, payload.document_ids)


@router.get("/signed-download")
def signed_download(token: str, request: Request, db: DBSession) -> FileResponse:
    context = get_request_audit_context(request)
    try:
        document_id = verify_download_token(token)
    except ValueError as exc:
        emit_document_audit_event(
            DocumentAuditEvent(
                action="signed_download",
                outcome="denied",
                actor=context.actor,
                request_id=context.request_id,
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    document = documents.get_document(db, document_id)
    path = documents.get_document_file_path(db, document_id)
    filename = document.metadata.get("original_filename") or document.title
    emit_document_audit_event(
        DocumentAuditEvent(
            action="signed_download",
            document_id=document_id,
            project_id=document.project_id,
            actor=context.actor,
            request_id=context.request_id,
            metadata={"filename": filename},
        )
    )
    return FileResponse(path, filename=filename)


@router.get("/{document_id}/download-token")
def document_download_token(document_id: UUID, request: Request, db: DBSession) -> dict[str, str | int]:
    document = documents.get_document(db, document_id)
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="download_token_issued",
            document_id=document_id,
            project_id=document.project_id,
            actor=context.actor,
            request_id=context.request_id,
            metadata={"expires_in": DEFAULT_TTL_SECONDS},
        )
    )
    return {"token": create_download_token(document_id), "expires_in": DEFAULT_TTL_SECONDS}


@router.get("/{document_id}", response_model=DocumentRead)
def read_document(document_id: UUID, db: DBSession) -> DocumentRead:
    return documents.get_document(db, document_id)


@router.get("/{document_id}/download")
def download_document(document_id: UUID, request: Request, db: DBSession) -> FileResponse:
    document = documents.get_document(db, document_id)
    path = documents.get_document_file_path(db, document_id)
    filename = document.metadata.get("original_filename") or document.title
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="direct_download",
            document_id=document_id,
            project_id=document.project_id,
            actor=context.actor,
            request_id=context.request_id,
            metadata={"filename": filename},
        )
    )
    return FileResponse(path, filename=filename)


@router.get("/{document_id}/integrity", response_model=DocumentIntegrity)
def document_integrity(document_id: UUID, db: DBSession) -> DocumentIntegrity:
    return documents.document_integrity(db, document_id)


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(document_id: UUID, payload: DocumentUpdate, db: DBSession) -> DocumentRead:
    return documents.update_document(db, document_id, payload)


@router.patch("/{document_id}/status", response_model=DocumentRead)
def update_document_status(
    document_id: UUID,
    payload: DocumentUpdateStatus,
    db: DBSession,
) -> DocumentRead:
    return documents.update_document_status(db, document_id, payload)
