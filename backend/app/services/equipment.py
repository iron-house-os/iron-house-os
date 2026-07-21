from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentCreate, EquipmentRead, EquipmentUpdate


def list_equipment(db: Session, status: str | None = None) -> list[EquipmentRead]:
    statement = select(Equipment).order_by(Equipment.name)
    if status:
        statement = statement.where(Equipment.status == status)
    return [_to_schema(item) for item in db.scalars(statement).all()]


def create_equipment(db: Session, payload: EquipmentCreate) -> EquipmentRead:
    item = Equipment(**payload.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return _to_schema(item)


def update_equipment(db: Session, equipment_id: UUID, payload: EquipmentUpdate) -> EquipmentRead:
    item = db.get(Equipment, equipment_id)
    if item is None:
        raise AppError("Equipment not found", status_code=404)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    _commit(db)
    db.refresh(item)
    return _to_schema(item)


def _to_schema(item: Equipment) -> EquipmentRead:
    normalized_status = (item.status or "").strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "operational": "available",
        "ready": "available",
        "active": "in_use",
        "working": "in_use",
        "deployed": "in_use",
        "repair": "maintenance",
        "out_of_service": "maintenance",
        "sold": "retired",
        "disposed": "retired",
    }
    normalized_status = aliases.get(normalized_status, normalized_status)
    if normalized_status not in {"available", "reserved", "in_use", "maintenance", "retired"}:
        normalized_status = "maintenance"
    return EquipmentRead(
        id=item.id,
        name=item.name,
        equipment_type=item.equipment_type,
        identifier=item.identifier,
        status=normalized_status,
        hourly_rate=float(item.hourly_rate) if item.hourly_rate is not None else None,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError("Equipment identifier already exists", status_code=409) from exc
