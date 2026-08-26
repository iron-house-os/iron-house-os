from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.help_feedback import HelpFeedback, HelpImprovement
from app.schemas.help_feedback import (
    HelpFeedbackCreate,
    HelpFeedbackEvidenceList,
    HelpFeedbackEvidenceRead,
    HelpFeedbackReceipt,
    HelpImprovementList,
    HelpImprovementRead,
    HelpImprovementStatusUpdate,
)
from app.services.auth import AuthenticatedUser
from app.services.help_coach import (
    APPROVED_HELP_ARTICLES,
    is_restricted_help_message,
    resolve_help_audience,
)


MANAGEMENT_ROLES = {"admin", "operations_manager"}


def record_help_feedback(
    db: Session,
    payload: HelpFeedbackCreate,
    user: AuthenticatedUser,
) -> HelpFeedbackReceipt:
    audience = resolve_help_audience(db, user)
    note = payload.note
    if note and is_restricted_help_message(note):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Do not include passwords, API keys, SINs, banking, medical, payroll, "
                "disciplinary, or restricted first-aid information in Help feedback."
            ),
        )

    allowed_source_ids = {
        article.id for article in APPROVED_HELP_ARTICLES if audience in article.audiences
    }
    invalid_source_ids = sorted(set(payload.source_ids) - allowed_source_ids)
    if invalid_source_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Feedback can reference only Help guides available to your access level.",
        )

    source_ids = sorted(payload.source_ids)
    route = payload.route.strip()
    group_key = _group_key(payload.feedback_type, route, source_ids)
    improvement = db.scalar(
        select(HelpImprovement).where(HelpImprovement.group_key == group_key)
    )
    if improvement is None:
        improvement = HelpImprovement(
            group_key=group_key,
            feedback_type=payload.feedback_type,
            route=route,
            source_ids_json=source_ids,
            evidence_count=0,
        )
        db.add(improvement)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            improvement = db.scalar(
                select(HelpImprovement).where(HelpImprovement.group_key == group_key)
            )
            if improvement is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Help feedback could not be recorded. Please try again.",
                )

    now = datetime.now(timezone.utc)
    values: dict[str, object] = {
        "evidence_count": HelpImprovement.evidence_count + 1,
        "last_seen_at": now,
    }
    if note:
        values["latest_note"] = note
    if payload.project_name:
        values["latest_project_name"] = payload.project_name
    db.execute(
        update(HelpImprovement).where(HelpImprovement.id == improvement.id).values(**values)
    )
    db.add(
        HelpFeedback(
            improvement_id=improvement.id,
            audience=audience,
            project_name=payload.project_name or None,
            note=note,
            created_by=user.email,
        )
    )
    db.commit()
    return HelpFeedbackReceipt(improvement_id=improvement.id)


def list_help_improvements(
    db: Session,
    user: AuthenticatedUser,
) -> HelpImprovementList:
    _require_management(user)
    rows = list(db.scalars(select(HelpImprovement).order_by(HelpImprovement.last_seen_at.desc())))
    return HelpImprovementList(items=[_read(row) for row in rows], total=len(rows))


def update_help_improvement(
    db: Session,
    improvement_id: UUID,
    payload: HelpImprovementStatusUpdate,
    user: AuthenticatedUser,
) -> HelpImprovementRead:
    _require_management(user)
    if payload.review_note and is_restricted_help_message(payload.review_note):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Do not include restricted information in an Improvement Inbox note.",
        )
    row = db.get(HelpImprovement, improvement_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Improvement not found.")
    row.status = payload.status
    row.review_note = payload.review_note
    row.reviewed_by = user.email
    row.reviewed_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _read(row)


def list_help_feedback_evidence(
    db: Session,
    improvement_id: UUID,
    user: AuthenticatedUser,
) -> HelpFeedbackEvidenceList:
    _require_management(user)
    if db.get(HelpImprovement, improvement_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Improvement not found.")
    rows = list(
        db.scalars(
            select(HelpFeedback)
            .where(HelpFeedback.improvement_id == improvement_id)
            .order_by(HelpFeedback.created_at.desc())
        )
    )
    return HelpFeedbackEvidenceList(
        items=[HelpFeedbackEvidenceRead.model_validate(row) for row in rows],
        total=len(rows),
    )


def _group_key(feedback_type: str, route: str, source_ids: list[str]) -> str:
    raw = "|".join((feedback_type, route or "/help", ",".join(source_ids)))
    return sha256(raw.encode()).hexdigest()


def _require_management(user: AuthenticatedUser) -> None:
    if user.role not in MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management Help access is required.",
        )


def _read(row: HelpImprovement) -> HelpImprovementRead:
    return HelpImprovementRead(
        id=row.id,
        feedback_type=row.feedback_type,
        route=row.route,
        source_ids=list(row.source_ids_json),
        status=row.status,
        evidence_count=row.evidence_count,
        last_seen_at=row.last_seen_at,
        latest_note=row.latest_note,
        latest_project_name=row.latest_project_name,
        review_note=row.review_note,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
    )
