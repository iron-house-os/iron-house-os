from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.finance import CustomerInvoice
from app.models.project import Project
from app.schemas.finance import (
    CustomerInvoiceCreate,
    CustomerInvoiceList,
    CustomerInvoiceRead,
    CustomerInvoiceStatusUpdate,
)
from app.services.auth import AuthenticatedUser
from app.services.finance import require_management

MONEY = Decimal("0.01")
STATUS_TRANSITIONS = {
    "draft": {"approved", "void"},
    "approved": {"draft", "issued", "void"},
    "issued": {"paid", "void"},
    "paid": set(),
    "void": set(),
}


def create_invoice(
    db: Session, payload: CustomerInvoiceCreate, user: AuthenticatedUser
) -> CustomerInvoiceRead:
    require_management(user)
    if payload.project_id and db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if db.scalar(select(CustomerInvoice).where(CustomerInvoice.invoice_number == payload.invoice_number)):
        raise HTTPException(status_code=409, detail="Invoice number already exists")
    values = _calculated_values(payload)
    invoice = CustomerInvoice(**values, status="draft", created_by=user.email)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return _read(invoice)


def list_invoices(db: Session, user: AuthenticatedUser) -> CustomerInvoiceList:
    require_management(user)
    _seed_nonproduction(db)
    rows = list(db.scalars(select(CustomerInvoice).order_by(CustomerInvoice.invoice_date.desc())))
    return CustomerInvoiceList(items=[_read(row) for row in rows], total=len(rows))


def get_invoice(db: Session, invoice_id: UUID, user: AuthenticatedUser) -> CustomerInvoiceRead:
    require_management(user)
    invoice = db.get(CustomerInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Customer invoice not found")
    return _read(invoice)


def update_status(
    db: Session,
    invoice_id: UUID,
    payload: CustomerInvoiceStatusUpdate,
    user: AuthenticatedUser,
) -> CustomerInvoiceRead:
    require_management(user)
    invoice = db.get(CustomerInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Customer invoice not found")
    if payload.status not in STATUS_TRANSITIONS.get(invoice.status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot move invoice from {invoice.status} to {payload.status}.")
    invoice.status = payload.status
    if payload.status == "issued":
        invoice.issued_by = user.email
        invoice.issued_at = datetime.now(UTC)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return _read(invoice)


def _decimal(value: str, label: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise HTTPException(status_code=422, detail=f"{label} must be a decimal number.") from exc
    if parsed < 0:
        raise HTTPException(status_code=422, detail=f"{label} cannot be negative.")
    return parsed


def _calculated_values(payload: CustomerInvoiceCreate) -> dict:
    items = []
    subtotal = Decimal("0")
    for item in payload.line_items:
        quantity = _decimal(item.quantity, "Quantity")
        unit_price = _decimal(item.unit_price, "Unit price")
        amount = (quantity * unit_price).quantize(MONEY, rounding=ROUND_HALF_UP)
        subtotal += amount
        items.append({"description": item.description, "quantity": str(quantity), "unit_price": f"{unit_price.quantize(MONEY):.2f}", "amount": f"{amount:.2f}"})
    subtotal = subtotal.quantize(MONEY, rounding=ROUND_HALF_UP)
    gst_rate = _decimal(payload.gst_rate, "GST rate")
    gst = (subtotal * gst_rate / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)
    values = payload.model_dump(exclude={"line_items", "gst_rate"})
    return {**values, "line_items_json": items, "subtotal": subtotal, "gst_rate": gst_rate, "gst": gst, "total": subtotal + gst}


def _read(invoice: CustomerInvoice) -> CustomerInvoiceRead:
    return CustomerInvoiceRead(
        id=invoice.id, invoice_number=invoice.invoice_number, project_id=invoice.project_id,
        project_name=invoice.project_name, site_address=invoice.site_address,
        customer_name=invoice.customer_name, customer_address=invoice.customer_address,
        customer_phone=invoice.customer_phone, invoice_date=invoice.invoice_date,
        due_date=invoice.due_date, terms=invoice.terms, status=invoice.status,
        line_items=invoice.line_items_json, subtotal=f"{Decimal(invoice.subtotal):.2f}",
        gst_rate=f"{Decimal(invoice.gst_rate):.2f}", gst=f"{Decimal(invoice.gst):.2f}",
        total=f"{Decimal(invoice.total):.2f}", development_seed_key=invoice.development_seed_key,
        created_by=invoice.created_by, issued_by=invoice.issued_by, issued_at=invoice.issued_at,
        created_at=invoice.created_at, updated_at=invoice.updated_at,
    )


def _seed_nonproduction(db: Session) -> None:
    if get_settings().environment.lower() not in {"development", "test", "testing"}:
        return
    seeds = (
        ("bennett-road", CustomerInvoiceCreate(invoice_number="DEV-BENNETT", project_name="Bennett Road", site_address="8640 Bennett Road, Unit 10, Richmond, BC V6Y 3T9", customer_name="AB-Tech Plumbing & Heating Ltd.", customer_address="8191 Dalemore Road, Richmond, BC V7C 2A5", customer_phone="604-241-4545", invoice_date=date(2026, 8, 10), due_date=date(2026, 9, 9), line_items=[{"description":"Original scope", "quantity":"1", "unit_price":"8600.00"}, {"description":"Hydrovac and dump fees", "quantity":"1", "unit_price":"2487.34"}, {"description":"Pump rental/dewatering setup", "quantity":"1", "unit_price":"475.00"}, {"description":"Pick up and install water boxes", "quantity":"1", "unit_price":"185.00"}])),
        ("bowline-common-excavation", CustomerInvoiceCreate(invoice_number="DEV-BOWLINE", project_name="Bowline common excavation", site_address=None, customer_name="Bowline Construction", customer_address="20526 50A Avenue, Langley, BC V3A 6Z2", customer_phone="778-808-3725", invoice_date=date(2026, 8, 14), due_date=date(2026, 9, 13), line_items=[{"description":"Common excavation - Aug 11", "quantity":"12.5", "unit_price":"220"}, {"description":"Common excavation - Aug 12", "quantity":"12", "unit_price":"220"}, {"description":"Common excavation - Aug 13", "quantity":"9", "unit_price":"220"}, {"description":"Common excavation - Aug 14", "quantity":"6", "unit_price":"220"}])),
        ("j-dewitt-hayward-dam-removal", CustomerInvoiceCreate(invoice_number="IH-2026-0824-JD", project_name="9557 Hayward St. - Dam Removal", site_address="9557 Hayward St.", customer_name="J. Dewitt", customer_address="9557 Hayward St.", invoice_date=date(2026, 8, 24), due_date=date(2026, 9, 23), terms="Net 30", gst_rate="5.00", line_items=[{"description":"Aug 17 - Machine delivery / biologist / dam removal", "quantity":"8", "unit_price":"130.00"}, {"description":"Aug 18 - Dam removal and load out spoils", "quantity":"8", "unit_price":"130.00"}, {"description":"Aug 19 - Continue dam removal and truck loading", "quantity":"8", "unit_price":"130.00"}, {"description":"Aug 20 - Dam removal, load out spoils and cleanup", "quantity":"10.5", "unit_price":"130.00"}])),
    )
    changed = False
    for key, payload in seeds:
        if db.scalar(select(CustomerInvoice.id).where(CustomerInvoice.development_seed_key == key)):
            continue
        db.add(CustomerInvoice(**_calculated_values(payload), status="draft", development_seed_key=key, created_by="development-seed@ironhousecivil.com"))
        changed = True
    if changed:
        db.commit()