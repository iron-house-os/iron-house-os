from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.db.session import get_db
from app.models.assistant import MeetingMinute
from app.models.project import Project
from app.schemas.meeting_minutes import (
    MeetingMinuteCreate,
    MeetingMinuteListItem,
    MeetingMinuteRead,
    MeetingMinutesDraft,
    MeetingMinutesDraftRequest,
    MeetingMinutesStatus,
)
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.meeting_minutes import (
    MAX_AUDIO_BYTES,
    MeetingMinutesUnavailable,
    draft_minutes,
    transcribe_audio,
)
from app.services.request_context import get_request_audit_context

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _require_management(user: CurrentUser) -> None:
    if user.role not in {"admin", "operations_manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management access is required.")


def _read_model(item: MeetingMinute) -> MeetingMinuteRead:
    return MeetingMinuteRead(
        id=item.id,
        owner_account_id=item.owner_account_id,
        project_id=item.project_id,
        title=item.title,
        meeting_date=item.meeting_date,
        attendees=item.attendees_json,
        transcript=item.transcript,
        summary=item.summary,
        priority_points=item.priority_points_json,
        decisions=item.decisions_json,
        action_items=item.action_items_json,
        transcription_model=item.transcription_model,
        summary_model=item.summary_model,
        status=item.status,
        consent_confirmed=item.consent_confirmed,
        review_confirmed=item.review_confirmed,
        audio_retained=item.audio_retained,
        created_by_email=item.created_by_email,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _list_model(item: MeetingMinute) -> MeetingMinuteListItem:
    return MeetingMinuteListItem(
        id=item.id,
        project_id=item.project_id,
        title=item.title,
        meeting_date=item.meeting_date,
        status=item.status,
        audio_retained=item.audio_retained,
        created_by_email=item.created_by_email,
        created_at=item.created_at,
    )


@router.get("/status", response_model=MeetingMinutesStatus)
def meeting_minutes_status(user: CurrentUser) -> MeetingMinutesStatus:
    _require_management(user)
    settings = get_settings()
    return MeetingMinutesStatus(
        enabled=settings.meeting_minutes_enabled,
        configured=bool(settings.openai_api_key),
        transcription_model=settings.openai_transcription_model,
        summary_model=settings.openai_chat_model,
        max_audio_bytes=MAX_AUDIO_BYTES,
        audio_retained=False,
    )


@router.post("/draft-from-audio", response_model=MeetingMinutesDraft)
async def draft_from_audio(
    request: Request,
    user: CurrentUser,
    audio: UploadFile = File(...),
    title: str = Form("Meeting"),
    attendees: str = Form(""),
    consent_confirmed: bool = Form(False),
) -> MeetingMinutesDraft:
    _require_management(user)
    if not get_settings().meeting_minutes_enabled:
        raise HTTPException(status_code=503, detail="Meeting Minutes is disabled.")
    if not consent_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Confirm that everyone present knows the meeting is being recorded.",
        )
    content_type = audio.content_type or ""
    content = await audio.read(MAX_AUDIO_BYTES + 1)
    try:
        transcript, transcription_model = transcribe_audio(content, content_type)
        draft = draft_minutes(
            transcript,
            title.strip()[:200] or "Meeting",
            [name.strip()[:255] for name in attendees.split(",") if name.strip()],
            transcription_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MeetingMinutesUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="meeting_minutes_draft",
            outcome="completed",
            actor=user.email,
            request_id=context.request_id,
            metadata={
                "source": "audio",
                "audio_bytes": len(content),
                "audio_retained": False,
                "transcription_model": transcription_model,
                "summary_model": draft.summary_model,
            },
        )
    )
    return draft


@router.post("/draft-from-transcript", response_model=MeetingMinutesDraft)
def draft_from_transcript(
    payload: MeetingMinutesDraftRequest,
    request: Request,
    user: CurrentUser,
) -> MeetingMinutesDraft:
    _require_management(user)
    if not get_settings().meeting_minutes_enabled:
        raise HTTPException(status_code=503, detail="Meeting Minutes is disabled.")
    if not payload.consent_confirmed:
        raise HTTPException(status_code=400, detail="Recording consent must be confirmed.")
    try:
        draft = draft_minutes(payload.transcript, payload.title, payload.attendees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MeetingMinutesUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="meeting_minutes_draft",
            outcome="completed",
            actor=user.email,
            request_id=context.request_id,
            metadata={
                "source": "transcript",
                "audio_retained": False,
                "summary_model": draft.summary_model,
            },
        )
    )
    return draft


@router.post("", response_model=MeetingMinuteRead, status_code=status.HTTP_201_CREATED)
def save_meeting_minutes(
    payload: MeetingMinuteCreate,
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> MeetingMinuteRead:
    _require_management(user)
    if not payload.consent_confirmed:
        raise HTTPException(status_code=400, detail="Recording consent must be confirmed.")
    if not payload.review_confirmed:
        raise HTTPException(status_code=400, detail="Management review must be confirmed before approval.")
    if payload.project_id is not None and db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    item = MeetingMinute(
        owner_account_id=user.id,
        project_id=payload.project_id,
        title=payload.title.strip(),
        meeting_date=payload.meeting_date,
        attendees_json=payload.attendees,
        transcript=payload.transcript.strip(),
        summary=payload.summary.strip(),
        priority_points_json=payload.priority_points,
        decisions_json=payload.decisions,
        action_items_json=[action.model_dump(mode="json") for action in payload.action_items],
        transcription_model=payload.transcription_model,
        summary_model=payload.summary_model,
        status="approved",
        consent_confirmed=True,
        review_confirmed=True,
        audio_retained=False,
        created_by_email=user.email,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="meeting_minutes_save",
            outcome="completed",
            actor=user.email,
            request_id=context.request_id,
            metadata={
                "meeting_minutes_id": str(item.id),
                "project_id": str(item.project_id) if item.project_id else None,
                "status": item.status,
                "review_confirmed": True,
                "audio_retained": False,
                "transcription_model": item.transcription_model,
                "summary_model": item.summary_model,
            },
        )
    )
    return _read_model(item)


@router.get("", response_model=list[MeetingMinuteListItem])
def list_meeting_minutes(user: CurrentUser, db: DBSession) -> list[MeetingMinuteListItem]:
    _require_management(user)
    items = db.scalars(
        select(MeetingMinute).order_by(MeetingMinute.meeting_date.desc()).limit(100)
    ).all()
    return [_list_model(item) for item in items]


@router.get("/{meeting_minutes_id}", response_model=MeetingMinuteRead)
def read_meeting_minutes(
    meeting_minutes_id: UUID,
    user: CurrentUser,
    db: DBSession,
) -> MeetingMinuteRead:
    _require_management(user)
    item = db.get(MeetingMinute, meeting_minutes_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Meeting minutes not found.")
    return _read_model(item)
