from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.legal import LegalAnalysis, LegalAuditEvent, LegalDeadline, LegalMatter
from app.schemas.legal import LegalDeadlineCreate, LegalMatterCreate
from app.services.legal_ai import LegalAIUnavailable, generate_legal_analysis
from app.services.legal_specialists import active_authorities, triage_specialists


def require_enabled() -> None:
    if not get_settings().legal_control_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="legal.control_disabled")


def _audit(
    db: Session,
    *,
    matter_id: UUID | None,
    actor: str,
    action: str,
    outcome: str = "completed",
    metadata: dict | None = None,
) -> None:
    db.add(
        LegalAuditEvent(
            matter_id=matter_id,
            occurred_at=datetime.now(UTC),
            actor=actor,
            action=action,
            outcome=outcome,
            metadata_json=metadata or {},
        )
    )


def create_matter(db: Session, payload: LegalMatterCreate, actor_id: UUID, actor_email: str) -> LegalMatter:
    require_enabled()
    specialists = triage_specialists(
        " ".join(filter(None, [payload.title, payload.matter_type, payload.project_name, payload.description]))
    )
    matter = LegalMatter(
        owner_account_id=actor_id,
        title=payload.title,
        matter_type=payload.matter_type,
        project_name=payload.project_name,
        counterparty=payload.counterparty,
        description=payload.description,
        confidentiality=payload.confidentiality,
        jurisdiction=payload.jurisdiction,
        assigned_specialists=specialists,
        created_by=actor_email,
    )
    db.add(matter)
    db.flush()
    _audit(db, matter_id=matter.id, actor=actor_email, action="legal_matter_created", metadata={"specialists": specialists})
    db.commit()
    db.refresh(matter)
    return matter


def list_matters(db: Session) -> list[LegalMatter]:
    require_enabled()
    return list(db.scalars(select(LegalMatter).order_by(LegalMatter.updated_at.desc()).limit(200)).all())


def get_matter(db: Session, matter_id: UUID) -> LegalMatter:
    require_enabled()
    matter = db.get(LegalMatter, matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Legal matter not found.")
    return matter


def get_analyses(db: Session, matter_id: UUID) -> list[LegalAnalysis]:
    return list(
        db.scalars(
            select(LegalAnalysis).where(LegalAnalysis.matter_id == matter_id).order_by(LegalAnalysis.created_at.desc())
        ).all()
    )


def get_deadlines(db: Session, matter_id: UUID) -> list[LegalDeadline]:
    return list(
        db.scalars(
            select(LegalDeadline).where(LegalDeadline.matter_id == matter_id).order_by(LegalDeadline.due_date)
        ).all()
    )


def analyse_matter(db: Session, matter_id: UUID, actor_email: str, question: str | None) -> LegalAnalysis:
    matter = get_matter(db, matter_id)
    if matter.confidentiality in {"personal_information", "privilege_requested"}:
        _audit(
            db,
            matter_id=matter.id,
            actor=actor_email,
            action="legal_analysis_requested",
            outcome="blocked",
            metadata={"reason": matter.confidentiality},
        )
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="Counsel/privacy review is required before this matter may be sent to the AI service.",
        )
    sources = active_authorities()
    try:
        draft = generate_legal_analysis(
            matter={
                "title": matter.title,
                "matter_type": matter.matter_type,
                "project_name": matter.project_name,
                "counterparty": matter.counterparty,
                "description": matter.description,
                "jurisdiction": matter.jurisdiction,
            },
            specialist_keys=matter.assigned_specialists,
            approved_sources=sources,
            question=question,
        )
    except LegalAIUnavailable as exc:
        _audit(db, matter_id=matter.id, actor=actor_email, action="legal_analysis_requested", outcome="unavailable")
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    analysis = LegalAnalysis(
        matter_id=matter.id,
        requested_by=actor_email,
        status="draft_requires_human_review",
        specialist_keys=matter.assigned_specialists,
        executive_summary=str(draft.get("executive_summary", "")),
        draft_text=str(draft["draft_text"]) if draft.get("draft_text") else None,
        issues=list(draft.get("issues", [])),
        recommendations=list(draft.get("recommendations", [])),
        questions_for_counsel=list(draft.get("questions_for_counsel", [])),
        source_ids=list(draft.get("source_ids", [])),
        disclaimer=str(draft["disclaimer"]),
    )
    risk_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    assessed = [
        str(item.get("risk", "")).lower()
        for item in analysis.issues
        if str(item.get("risk", "")).lower() in risk_rank
    ]
    if assessed:
        matter.risk_level = max(assessed, key=lambda value: risk_rank[value])
    matter.status = "review"
    db.add(analysis)
    _audit(
        db,
        matter_id=matter.id,
        actor=actor_email,
        action="legal_analysis_created",
        metadata={"source_ids": analysis.source_ids, "specialists": analysis.specialist_keys},
    )
    db.commit()
    db.refresh(analysis)
    return analysis


def create_deadline(
    db: Session, matter_id: UUID, payload: LegalDeadlineCreate, actor_email: str
) -> LegalDeadline:
    get_matter(db, matter_id)
    deadline = LegalDeadline(
        matter_id=matter_id,
        title=payload.title,
        due_date=payload.due_date,
        source_basis=payload.source_basis,
        status="candidate",
        created_by=actor_email,
    )
    db.add(deadline)
    db.flush()
    _audit(db, matter_id=matter_id, actor=actor_email, action="legal_deadline_candidate_created")
    db.commit()
    db.refresh(deadline)
    return deadline


def verify_deadline(
    db: Session, deadline_id: UUID, actor_email: str, evidence_reference: str
) -> LegalDeadline:
    require_enabled()
    deadline = db.get(LegalDeadline, deadline_id)
    if deadline is None:
        raise HTTPException(status_code=404, detail="Legal deadline not found.")
    deadline.status = "verified"
    deadline.verified_by = actor_email
    deadline.verified_at = datetime.now(UTC)
    deadline.evidence_reference = evidence_reference
    _audit(
        db,
        matter_id=deadline.matter_id,
        actor=actor_email,
        action="legal_deadline_verified",
        metadata={"deadline_id": str(deadline.id), "evidence_reference": evidence_reference},
    )
    db.commit()
    db.refresh(deadline)
    return deadline


def candidate_deadline_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(LegalDeadline).where(LegalDeadline.status == "candidate")) or 0)
