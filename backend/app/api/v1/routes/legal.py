from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AdminUser
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.legal import (
    LegalAnalysisRead,
    LegalAnalysisRequest,
    LegalDashboard,
    LegalDeadlineCreate,
    LegalDeadlineRead,
    LegalDeadlineVerify,
    LegalMatterCreate,
    LegalMatterDetail,
    LegalMatterRead,
)
from app.services import legal
from app.services.legal_specialists import authority_catalogue, specialist_catalogue


router = APIRouter()


@router.get("/dashboard", response_model=LegalDashboard)
def dashboard(user: AdminUser, db: Session = Depends(get_db)) -> LegalDashboard:
    legal.require_enabled()
    settings = get_settings()
    return LegalDashboard(
        enabled=settings.legal_control_enabled,
        configured=bool(settings.openai_api_key),
        mode="supervised_draft_only",
        matters=legal.list_matters(db),
        specialists=specialist_catalogue(),
        authorities=authority_catalogue(),
        candidate_deadline_count=legal.candidate_deadline_count(db),
    )


@router.get("/matters", response_model=list[LegalMatterRead])
def matters(user: AdminUser, db: Session = Depends(get_db)):
    return legal.list_matters(db)


@router.post("/matters", response_model=LegalMatterRead, status_code=201)
def create_matter(payload: LegalMatterCreate, user: AdminUser, db: Session = Depends(get_db)):
    return legal.create_matter(db, payload, user.id, user.email)


@router.get("/matters/{matter_id}", response_model=LegalMatterDetail)
def matter_detail(matter_id: UUID, user: AdminUser, db: Session = Depends(get_db)):
    matter = legal.get_matter(db, matter_id)
    return LegalMatterDetail(
        **LegalMatterRead.model_validate(matter).model_dump(),
        analyses=legal.get_analyses(db, matter_id),
        deadlines=legal.get_deadlines(db, matter_id),
    )


@router.post("/matters/{matter_id}/analyse", response_model=LegalAnalysisRead, status_code=201)
def analyse(
    matter_id: UUID,
    payload: LegalAnalysisRequest,
    user: AdminUser,
    db: Session = Depends(get_db),
):
    return legal.analyse_matter(db, matter_id, user.email, payload.question)


@router.post("/matters/{matter_id}/deadlines", response_model=LegalDeadlineRead, status_code=201)
def add_deadline(
    matter_id: UUID,
    payload: LegalDeadlineCreate,
    user: AdminUser,
    db: Session = Depends(get_db),
):
    return legal.create_deadline(db, matter_id, payload, user.email)


@router.post("/deadlines/{deadline_id}/verify", response_model=LegalDeadlineRead)
def verify_deadline(
    deadline_id: UUID,
    payload: LegalDeadlineVerify,
    user: AdminUser,
    db: Session = Depends(get_db),
):
    return legal.verify_deadline(db, deadline_id, user.email, payload.evidence_reference)
