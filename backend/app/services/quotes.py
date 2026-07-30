from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.project import Project
from app.models.rfq import Quote, RFQ, RFQPackage
from app.models.supplier import Supplier
from app.schemas.quote_integration import (
    SupplierQuoteRead,
    SupplierQuoteRecordCreate,
    SupplierQuoteUpdate,
)


def list_quotes(db: Session, project_id: UUID) -> list[SupplierQuoteRead]:
    _require_project(db, project_id)
    quotes = db.scalars(
        select(Quote)
        .where(Quote.project_id == project_id)
        .order_by(Quote.created_at, Quote.supplier_name, Quote.revision)
    ).all()
    return [_to_schema(quote) for quote in quotes]


def create_quote(db: Session, payload: SupplierQuoteRecordCreate) -> SupplierQuoteRead:
    _validate_links(
        db,
        project_id=payload.project_id,
        rfq_id=payload.rfq_id,
        rfq_package_id=payload.rfq_package_id,
        supplier_id=payload.supplier_id,
    )
    quote = Quote(
        project_id=payload.project_id,
        **payload.model_dump(exclude={"project_id"}),
    )
    _normalise_model(quote)
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return _to_schema(quote)


def update_quote(
    db: Session,
    quote_id: UUID,
    payload: SupplierQuoteUpdate,
) -> SupplierQuoteRead:
    quote = _load_quote(db, quote_id)
    changes = payload.model_dump(exclude_unset=True)
    _validate_links(
        db,
        project_id=quote.project_id,
        rfq_id=changes.get("rfq_id", quote.rfq_id),
        rfq_package_id=changes.get("rfq_package_id", quote.rfq_package_id),
        supplier_id=changes.get("supplier_id", quote.supplier_id),
    )
    for key, value in changes.items():
        setattr(quote, key, value)
    _normalise_model(quote)
    db.commit()
    db.refresh(quote)
    return _to_schema(quote)


def _validate_links(
    db: Session,
    *,
    project_id: UUID,
    rfq_id: UUID | None,
    rfq_package_id: UUID | None,
    supplier_id: UUID | None,
) -> None:
    _require_project(db, project_id)
    if rfq_id is not None:
        rfq = db.get(RFQ, rfq_id)
        if rfq is None:
            raise AppError("RFQ not found", status_code=404)
        if rfq.project_id != project_id:
            raise AppError("RFQ does not belong to the selected project", status_code=409)
    if rfq_package_id is not None:
        rfq_package = db.get(RFQPackage, rfq_package_id)
        if rfq_package is None:
            raise AppError("RFQ package not found", status_code=404)
        if rfq_package.project_id != project_id:
            raise AppError(
                "RFQ package does not belong to the selected project",
                status_code=409,
            )
    if supplier_id is not None and db.get(Supplier, supplier_id) is None:
        raise AppError("Supplier not found", status_code=404)


def _require_project(db: Session, project_id: UUID) -> None:
    if db.get(Project, project_id) is None:
        raise AppError("Project not found", status_code=404)


def _load_quote(db: Session, quote_id: UUID) -> Quote:
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise AppError("Supplier quote not found", status_code=404)
    return quote


def _normalise_model(quote: Quote) -> None:
    quote.supplier_name = quote.supplier_name.strip()
    quote.scope = quote.scope.strip()
    quote.quote_reference = _clean_optional(quote.quote_reference)
    quote.line_item_code = _clean_optional(quote.line_item_code)
    quote.line_item_description = _clean_optional(quote.line_item_description)
    quote.selection_reason = _clean_optional(quote.selection_reason)
    quote.notes = _clean_optional(quote.notes)
    quote.qualification_notes = _clean_list(quote.qualification_notes)
    quote.exclusions = _clean_list(quote.exclusions)


def _clean_optional(value: str | None) -> str | None:
    cleaned = value.strip() if value else ""
    return cleaned or None


def _clean_list(values: list[str] | None) -> list[str]:
    return [item.strip() for item in values or [] if item.strip()]


def _to_schema(quote: Quote) -> SupplierQuoteRead:
    return SupplierQuoteRead(
        id=quote.id,
        project_id=quote.project_id,
        rfq_id=quote.rfq_id,
        rfq_package_id=quote.rfq_package_id,
        supplier_id=quote.supplier_id,
        supplier_name=quote.supplier_name,
        quote_reference=quote.quote_reference,
        revision=quote.revision,
        line_item_code=quote.line_item_code,
        line_item_description=quote.line_item_description,
        scope=quote.scope,
        scope_type=quote.scope_type,
        status=quote.status,
        amount=float(quote.amount or 0),
        is_qualified=quote.is_qualified,
        qualification_notes=quote.qualification_notes or [],
        is_selected=quote.is_selected,
        selection_reason=quote.selection_reason,
        exclusions=quote.exclusions or [],
        notes=quote.notes,
        created_at=quote.created_at,
        updated_at=quote.updated_at,
    )
