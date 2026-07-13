from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.drawing_intelligence import (
    CivilDrawingAnalysis,
    CivilDrawingAnalysisList,
    CivilDrawingReanalyzeRequest,
    DrawingSetAnalyzeRequest,
    DrawingSetAnalysisResponse,
)
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.drawing_intelligence import (
    analyze_drawing_set,
    get_civil_pdf_analysis,
    ingest_civil_pdf,
    list_project_civil_pdf_analyses,
    reanalyze_civil_pdf,
)
from app.services.request_context import get_request_audit_context

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("/analyze", response_model=DrawingSetAnalysisResponse)
def analyze(payload: DrawingSetAnalyzeRequest) -> DrawingSetAnalysisResponse:
    return analyze_drawing_set(payload)


@router.post(
    "/ingest",
    response_model=CivilDrawingAnalysis,
    status_code=status.HTTP_201_CREATED,
)
async def ingest(
    request: Request,
    db: DBSession,
    file: UploadFile = File(...),
    project_id: UUID = Form(...),
    title: str | None = Form(default=None),
    municipality: str | None = Form(default=None),
) -> CivilDrawingAnalysis:
    report = await ingest_civil_pdf(
        db,
        file=file,
        project_id=project_id,
        title=title,
        municipality=municipality,
    )
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="drawing_ingest_analyze",
            document_id=report.source.document_id,
            project_id=report.source.project_id,
            actor=context.actor,
            request_id=context.request_id,
            metadata={
                "filename": report.source.original_filename,
                "sha256_hash": report.source.sha256_hash,
                "page_count": report.source.page_count,
                "extraction_status": report.extraction_status,
                "quantity_candidate_count": len(report.quantity_candidates),
            },
        )
    )
    return report


@router.get(
    "/projects/{project_id}",
    response_model=CivilDrawingAnalysisList,
)
def list_project_analyses(
    project_id: UUID,
    db: DBSession,
) -> CivilDrawingAnalysisList:
    return list_project_civil_pdf_analyses(db, project_id)


@router.get("/{document_id}", response_model=CivilDrawingAnalysis)
def read_analysis(document_id: UUID, db: DBSession) -> CivilDrawingAnalysis:
    return get_civil_pdf_analysis(db, document_id)


@router.post("/{document_id}/reanalyze", response_model=CivilDrawingAnalysis)
def reanalyze(
    document_id: UUID,
    payload: CivilDrawingReanalyzeRequest,
    db: DBSession,
) -> CivilDrawingAnalysis:
    return reanalyze_civil_pdf(db, document_id, payload.municipality)
