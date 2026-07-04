from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.contact import Contact
from app.models.supplier import Supplier
from app.schemas.supplier import (
    ContactCreate,
    ContactRead,
    SupplierCreate,
    SupplierRead,
    SupplierUpdate,
)


def create_supplier(db: Session, payload: SupplierCreate) -> SupplierRead:
    supplier = Supplier(
        name=payload.name,
        category=payload.category,
        service_area=payload.service_area,
        website=payload.website,
        notes=payload.notes,
        metadata_json=payload.metadata,
    )
    supplier.contacts = [_contact_from_payload(contact) for contact in payload.contacts]
    db.add(supplier)
    db.commit()
    return _to_schema(_load_supplier(db, supplier.id))


def bulk_create_suppliers(db: Session, payload: list[SupplierCreate]) -> list[SupplierRead]:
    created = [create_supplier(db, supplier) for supplier in payload]
    return created


def list_suppliers(
    db: Session,
    search: str | None = None,
    category: str | None = None,
    service_area: str | None = None,
) -> list[SupplierRead]:
    statement = select(Supplier).options(selectinload(Supplier.contacts)).order_by(Supplier.name)
    if search:
        search_term = f"%{search}%"
        statement = statement.where(
            or_(
                Supplier.name.ilike(search_term),
                Supplier.category.ilike(search_term),
                Supplier.service_area.ilike(search_term),
            )
        )
    if category:
        statement = statement.where(Supplier.category == category)
    if service_area:
        statement = statement.where(Supplier.service_area == service_area)
    return [_to_schema(supplier) for supplier in db.scalars(statement).all()]


def get_supplier(db: Session, supplier_id: UUID) -> SupplierRead:
    return _to_schema(_load_supplier(db, supplier_id))


def update_supplier(db: Session, supplier_id: UUID, payload: SupplierUpdate) -> SupplierRead:
    supplier = _load_supplier(db, supplier_id)
    update_data = payload.model_dump(exclude_unset=True)
    metadata = update_data.pop("metadata", None)
    for key, value in update_data.items():
        setattr(supplier, key, value)
    if metadata is not None:
        supplier.metadata_json = metadata
    db.commit()
    return _to_schema(_load_supplier(db, supplier_id))


def replace_supplier_contacts(
    db: Session,
    supplier_id: UUID,
    payload: list[ContactCreate],
) -> SupplierRead:
    _load_supplier(db, supplier_id)
    db.execute(delete(Contact).where(Contact.supplier_id == supplier_id))
    db.add_all(
        Contact(
            supplier_id=supplier_id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            phone=contact.phone,
            role=contact.role,
        )
        for contact in payload
    )
    db.commit()
    return _to_schema(_load_supplier(db, supplier_id))


def _load_supplier(db: Session, supplier_id: UUID) -> Supplier:
    supplier = db.scalar(
        select(Supplier).where(Supplier.id == supplier_id).options(selectinload(Supplier.contacts))
    )
    if supplier is None:
        raise AppError("Supplier not found", status_code=404)
    return supplier


def _contact_from_payload(payload: ContactCreate) -> Contact:
    return Contact(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        role=payload.role,
    )


def _to_schema(supplier: Supplier) -> SupplierRead:
    return SupplierRead(
        id=supplier.id,
        name=supplier.name,
        category=supplier.category,
        service_area=supplier.service_area,
        website=supplier.website,
        notes=supplier.notes,
        metadata=supplier.metadata_json or {},
        contacts=[
            ContactRead(
                id=contact.id,
                first_name=contact.first_name,
                last_name=contact.last_name,
                email=contact.email,
                phone=contact.phone,
                role=contact.role,
            )
            for contact in supplier.contacts
        ],
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
    )
