from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.db.session import get_db
from app.models.assistant import AssistantConversation, AssistantMessage, ProjectMemory
from app.schemas.assistant import (
    AssistantConversationRead,
    AssistantPrompt,
    AssistantReply,
    AssistantStatus,
    MemoryImportResult,
    ProjectMemoryRead,
)
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.iron_house_chat import AssistantUnavailable, generate_help_reply
from app.services.project_brain import (
    format_memory_context,
    import_chatgpt_export,
    memory_count,
    relevant_memory,
    search_memory,
    seed_canonical_memory,
)
from app.services.request_context import get_request_audit_context

router = APIRouter()


def _require_management(user: CurrentUser) -> None:
    if user.role not in {"admin", "operations_manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management access is required.")


@router.get("/status", response_model=AssistantStatus)
def assistant_status(user: CurrentUser, db: Session = Depends(get_db)) -> AssistantStatus:
    _require_management(user)
    settings = get_settings()
    seed_canonical_memory(db)
    return AssistantStatus(
        enabled=settings.iron_house_chat_enabled,
        configured=bool(settings.openai_api_key),
        model=settings.openai_chat_model,
        mode="read-only",
        memory_count=memory_count(db),
    )


@router.get("/brain", response_model=list[ProjectMemoryRead])
def list_project_brain(user: CurrentUser, db: Session = Depends(get_db)):
    _require_management(user)
    seed_canonical_memory(db)
    return db.scalars(select(ProjectMemory).order_by(
        ProjectMemory.authority.desc(), ProjectMemory.source_date.desc()
    ).limit(200)).all()


@router.get("/brain/search", response_model=list[ProjectMemoryRead])
def search_project_brain(
    user: CurrentUser,
    db: Session = Depends(get_db),
    q: str = Query(default="", max_length=500),
    source_kind: str | None = Query(default=None, max_length=40),
    min_authority: int = Query(default=0, ge=0, le=100),
    limit: int = Query(default=25, ge=1, le=100),
):
    _require_management(user)
    seed_canonical_memory(db)
    return search_memory(
        db,
        query=q,
        source_kind=source_kind,
        min_authority=min_authority,
        limit=limit,
    )


@router.post("/brain/import-chatgpt", response_model=MemoryImportResult)
async def import_project_chats(request: Request, user: CurrentUser, db: Session = Depends(get_db),
                               export: UploadFile = File(...)):
    _require_management(user)
    try:
        result = import_chatgpt_export(db, await export.read(), export.filename or "conversations.json", user.email)
    except (ValueError, UnicodeDecodeError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    context = get_request_audit_context(request)
    emit_document_audit_event(DocumentAuditEvent(
        action="project_brain_import", outcome="completed", actor=user.email,
        request_id=context.request_id,
        metadata={"imported": result["imported"], "updated": result["updated"], "skipped": result["skipped"]},
    ))
    return MemoryImportResult(**result)


@router.get("/conversations", response_model=list[AssistantConversationRead])
def list_conversations(user: CurrentUser, db: Session = Depends(get_db)):
    _require_management(user)
    return db.scalars(
        select(AssistantConversation)
        .where(AssistantConversation.owner_account_id == user.id)
        .order_by(AssistantConversation.updated_at.desc())
        .limit(50)
    ).all()


@router.get("/conversations/{conversation_id}/messages", response_model=list[dict])
def list_messages(conversation_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    _require_management(user)
    conversation = db.scalar(
        select(AssistantConversation).where(
            AssistantConversation.id == conversation_id,
            AssistantConversation.owner_account_id == user.id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    messages = db.scalars(
        select(AssistantMessage)
        .where(AssistantMessage.conversation_id == conversation_id)
        .order_by(AssistantMessage.created_at)
    ).all()
    return [{"id": str(item.id), "role": item.role, "content": item.content,
             "status": item.status, "created_at": item.created_at} for item in messages]


@router.post("/messages", response_model=AssistantReply)
def send_message(payload: AssistantPrompt, request: Request, user: CurrentUser, db: Session = Depends(get_db)):
    _require_management(user)
    settings = get_settings()
    if not settings.iron_house_chat_enabled:
        raise HTTPException(status_code=503, detail="Iron House Chat is disabled.")
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(select(AssistantConversation).where(
            AssistantConversation.id == payload.conversation_id,
            AssistantConversation.owner_account_id == user.id,
        ))
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    if conversation is None:
        conversation = AssistantConversation(
            owner_account_id=user.id,
            title=payload.message.strip()[:80],
        )
        db.add(conversation)
        db.flush()
    user_message = AssistantMessage(
        conversation_id=conversation.id, actor_account_id=user.id, role="user",
        content=payload.message.strip(), status="completed",
    )
    db.add(user_message)
    db.flush()
    history = db.scalars(select(AssistantMessage).where(
        AssistantMessage.conversation_id == conversation.id
    ).order_by(AssistantMessage.created_at.desc()).limit(12)).all()
    provider_messages = [{"role": item.role, "content": item.content} for item in reversed(history)]
    seed_canonical_memory(db)
    memories = relevant_memory(db, payload.message)
    try:
        answer = generate_help_reply(provider_messages, format_memory_context(memories))
        answer_status = "completed"
    except AssistantUnavailable as exc:
        answer = str(exc)
        answer_status = "unavailable"
    assistant_message = AssistantMessage(
        conversation_id=conversation.id, actor_account_id=user.id, role="assistant",
        content=answer, status=answer_status,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(conversation)
    db.refresh(user_message)
    db.refresh(assistant_message)
    context = get_request_audit_context(request)
    emit_document_audit_event(DocumentAuditEvent(
        action="assistant_help_request", outcome=answer_status, actor=user.email,
        request_id=context.request_id,
        metadata={"conversation_id": str(conversation.id), "mode": "read-only", "model": settings.openai_chat_model,
                  "memory_sources": [item.source_id for item in memories]},
    ))
    return AssistantReply(conversation=conversation, user_message=user_message, assistant_message=assistant_message)
