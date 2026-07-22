from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.db.session import get_db
from app.models.assistant import AssistantConversation, AssistantMessage
from app.schemas.assistant import (
    AssistantConversationRead,
    AssistantPrompt,
    AssistantReply,
    AssistantStatus,
)
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.iron_house_chat import AssistantUnavailable, generate_help_reply
from app.services.request_context import get_request_audit_context
from fastapi import Depends

router = APIRouter()


def _require_management(user: CurrentUser) -> None:
    if user.role not in {"admin", "operations_manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management access is required.")


@router.get("/status", response_model=AssistantStatus)
def assistant_status(user: CurrentUser) -> AssistantStatus:
    _require_management(user)
    settings = get_settings()
    return AssistantStatus(
        enabled=settings.iron_house_chat_enabled,
        configured=bool(settings.openai_api_key),
        model=settings.openai_chat_model,
        mode="read-only",
    )


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
    try:
        answer = generate_help_reply(provider_messages)
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
        metadata={"conversation_id": str(conversation.id), "mode": "read-only", "model": settings.openai_chat_model},
    ))
    return AssistantReply(conversation=conversation, user_message=user_message, assistant_message=assistant_message)

