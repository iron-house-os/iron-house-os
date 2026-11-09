from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.daily_timesheet import DailyTimesheetAction, DailyTimesheetBootstrap, DailyTimesheetRead, DailyTimesheetRevision, DailyTimesheetWrite
from app.services import daily_timesheets
from app.services.daily_timesheet_pdf import render_daily_timesheet_pdf


router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.get("/bootstrap", response_model=DailyTimesheetBootstrap)
def bootstrap(db: DBSession, user: CurrentUser) -> DailyTimesheetBootstrap:
    return daily_timesheets.bootstrap(db, user)


@router.post("", response_model=DailyTimesheetRead, status_code=status.HTTP_201_CREATED)
def create(payload: DailyTimesheetWrite, db: DBSession, user: CurrentUser) -> DailyTimesheetRead:
    return daily_timesheets.save_draft(db, payload, user)


@router.put("/{sheet_id}", response_model=DailyTimesheetRead)
def update(sheet_id: UUID, payload: DailyTimesheetWrite, db: DBSession, user: CurrentUser) -> DailyTimesheetRead:
    return daily_timesheets.save_draft(db, payload, user, sheet_id)


@router.post("/{sheet_id}/submit", response_model=DailyTimesheetRead)
def submit(sheet_id: UUID, db: DBSession, user: CurrentUser) -> DailyTimesheetRead:
    return daily_timesheets.submit(db, sheet_id, user)


@router.post("/{sheet_id}/revision", response_model=DailyTimesheetRead, status_code=status.HTTP_201_CREATED)
def revision(sheet_id: UUID, payload: DailyTimesheetRevision, db: DBSession, user: CurrentUser) -> DailyTimesheetRead:
    return daily_timesheets.create_revision(db, sheet_id, payload, user)


@router.post("/{sheet_id}/actions/{action}", response_model=DailyTimesheetRead)
def action(sheet_id: UUID, action: str, payload: DailyTimesheetAction, db: DBSession, user: CurrentUser) -> DailyTimesheetRead:
    if action not in {"approve", "reject", "void", "reopen"}:
        raise HTTPException(status_code=404, detail="Unknown daily sheet action.")
    return daily_timesheets.decide(db, sheet_id, action, payload, user)


@router.post("/{sheet_id}/post", response_model=DailyTimesheetRead)
def post(sheet_id: UUID, db: DBSession, user: CurrentUser) -> DailyTimesheetRead:
    return daily_timesheets.post_time_entries(db, sheet_id, user)


@router.post("/{sheet_id}/export.csv")
def export_csv(sheet_id: UUID, db: DBSession, user: CurrentUser) -> Response:
    filename, content = daily_timesheets.export_csv(db, sheet_id, user)
    return Response(content=content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{sheet_id}/export.pdf")
def export_pdf(sheet_id: UUID, db: DBSession, user: CurrentUser) -> Response:
    record = daily_timesheets.get_for_pdf(db, sheet_id, user)
    return Response(content=render_daily_timesheet_pdf(record), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="daily-timesheet-{record.work_date}-v{(record.details or {}).get("version", 1)}.pdf"'})
