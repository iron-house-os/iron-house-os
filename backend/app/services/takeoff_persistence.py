from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Takeoff
from app.models.project import Project
from app.schemas.takeoff_persistence import TakeoffList, TakeoffRead, TakeoffSaveRequest


def save_takeoff(db: Session, payload: TakeoffSaveRequest) -> TakeoffRead:
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    quantities = {
        "items": [item.model_dump(mode="json") for item in payload.items],
        "engine_result": payload.engine_result.model_dump(mode="json") if payload.engine_result else None,
        "quantity_register": payload.quantity_register.model_dump(mode="json") if payload.quantity_register else None,
    }
    takeoff = Takeoff(
        project_id=payload.project_id,
        drawing_id=payload.drawing_id,
        status=payload.status,
        notes=payload.notes,
        quantities_json=quantities,
    )
    db.add(takeoff)
    db.commit()
    db.refresh(takeoff)
    return _to_read(takeoff)


def list_project_takeoffs(db: Session, project_id: UUID) -> TakeoffList:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    rows = db.scalars(select(Takeoff).where(Takeoff.project_id == project_id).order_by(Takeoff.created_at.desc())).all()
    return TakeoffList(items=[_to_read(row) for row in rows], total=len(rows))


def get_takeoff(db: Session, takeoff_id: UUID) -> TakeoffRead:
    takeoff = db.get(Takeoff, takeoff_id)
    if not takeoff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Takeoff not found")
    return _to_read(takeoff)


def _to_read(takeoff: Takeoff) -> TakeoffRead:
    return TakeoffRead(
        id=takeoff.id,
        project_id=takeoff.project_id,
        drawing_id=takeoff.drawing_id,
        status=takeoff.status,
        notes=takeoff.notes,
        quantities=takeoff.quantities_json or {},
        created_at=takeoff.created_at,
        updated_at=takeoff.updated_at,
    )
