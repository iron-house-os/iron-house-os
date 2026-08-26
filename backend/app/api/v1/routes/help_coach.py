from time import perf_counter

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.assistant import HelpCoachPrompt, HelpCoachReply, HelpCoachSource
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.help_coach import (
    format_help_context,
    is_restricted_help_message,
    resolve_help_audience,
    select_help_articles,
    static_help_answer,
)
from app.services.iron_house_chat import AssistantUnavailable, generate_help_coach_reply
from app.services.request_context import get_request_audit_context


router = APIRouter()


@router.post("/messages", response_model=HelpCoachReply)
def ask_help_coach(
    payload: HelpCoachPrompt,
    request: Request,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> HelpCoachReply:
    started = perf_counter()
    audience = resolve_help_audience(db, user)
    articles = []
    provider_status = "not_called"

    if is_restricted_help_message(payload.message):
        answer = (
            "Do not enter passwords, API keys, SINs, banking, medical, payroll, disciplinary, "
            "or restricted first-aid information in Help. Contact your supervisor or management "
            "through the approved private process."
        )
        answer_status = "restricted"
    else:
        articles = select_help_articles(payload.message, audience, payload.route)
        if not articles:
            answer = (
                "I could not find an approved Help guide for that question. Try a shorter term in "
                "Search Help below, or ask your supervisor. I cannot guess or change an OS record."
            )
            answer_status = "no_match"
        else:
            answer = static_help_answer(articles[0])
            answer_status = "static_fallback"
            settings = get_settings()
            if settings.iron_house_chat_enabled and settings.openai_api_key:
                provider_status = "requested"
                try:
                    answer = generate_help_coach_reply(
                        payload.message,
                        format_help_context(articles),
                        route=payload.route,
                        project_name=payload.project_name,
                    )
                    answer_status = "completed"
                    provider_status = "completed"
                except AssistantUnavailable:
                    provider_status = "unavailable"

    sources = [
        HelpCoachSource(id=article.id, title=article.title, path=article.path)
        for article in articles
    ]
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="help_coach_request",
            outcome=answer_status,
            actor=user.email,
            request_id=context.request_id,
            metadata={
                "audience": audience,
                "latency_ms": round((perf_counter() - started) * 1000),
                "mode": "read-only",
                "provider_status": provider_status,
                "route": payload.route,
                "source_ids": [source.id for source in sources],
            },
        )
    )
    return HelpCoachReply(
        answer=answer,
        status=answer_status,
        audience=audience,
        sources=sources,
    )
