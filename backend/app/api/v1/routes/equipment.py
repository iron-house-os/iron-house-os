from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.equipment import EquipmentCreate, EquipmentList, EquipmentRead, EquipmentUpdate
from app.services import equipment

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=EquipmentList)
def list_equipment(
    db: DBSession,
    equipment_status: str | None = Query(default=None, alias="status"),
) -> EquipmentList:
    items = equipment.list_equipment(db, status=equipment_status)
    return EquipmentList(items=items, total=len(items))


@router.post("", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
def create_equipment(payload: EquipmentCreate, db: DBSession) -> EquipmentRead:
    return equipment.create_equipment(db, payload)


@router.patch("/{equipment_id}", response_model=EquipmentRead)
def update_equipment(
    equipment_id: UUID,
    payload: EquipmentUpdate,
    db: DBSession,
) -> EquipmentRead:
    return equipment.update_equipment(db, equipment_id, payload)
