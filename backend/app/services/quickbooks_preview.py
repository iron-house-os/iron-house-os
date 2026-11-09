"""Read-only preflight for a future QuickBooks Online invoice transfer.

This module intentionally has no Intuit client and cannot post accounting data.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finance import CustomerInvoice
from app.models.project import Project
from app.schemas.finance import QuickBooksInvoicePreview
from app.services.auth import AuthenticatedUser
from app.services.finance import require_management

CENT = Decimal("0.01")


def _money(value: object) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid monetary value") from exc
    if not number.is_finite() or number < 0:
        raise ValueError("Invalid monetary value")
    return number.quantize(CENT, rounding=ROUND_HALF_UP)


def preview_invoice(db: Session, invoice_id: UUID, user: AuthenticatedUser) -> QuickBooksInvoicePreview:
    require_management(user)
    invoice = db.get(CustomerInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Customer invoice not found")

    blockers: list[str] = []
    if invoice.status != "issued" or not invoice.issued_by or not invoice.issued_at:
        blockers.append("The invoice must be issued with a recorded issuer before accounting export.")
    if invoice.development_seed_key:
        blockers.append("Development seed invoices cannot be exported.")
    if not invoice.project_id:
        blockers.append("Link the invoice to a real IHOS project.")
    else:
        project = db.get(Project, invoice.project_id)
        if project is None or project.deleted_at or project.status not in {"awarded", "construction", "completed"}:
            blockers.append("The linked project must be active, awarded or completed, and outside Trash.")
    if not invoice.invoice_number.strip() or not invoice.customer_name.strip():
        blockers.append("An invoice number and customer are required.")
    count = db.scalar(select(func.count()).select_from(CustomerInvoice).where(
        CustomerInvoice.invoice_number == invoice.invoice_number
    ))
    if count != 1:
        blockers.append("The IHOS invoice number must be unique.")

    lines: list[dict[str, str]] = []
    try:
        subtotal = Decimal("0.00")
        if not invoice.line_items_json:
            raise ValueError("No invoice lines")
        for index, line in enumerate(invoice.line_items_json, start=1):
            quantity = Decimal(str(line["quantity"]))
            unit_price = _money(line["unit_price"])
            amount = _money(line["amount"])
            if not quantity.is_finite() or quantity <= 0 or not str(line.get("description", "")).strip():
                raise ValueError("Invalid invoice line")
            if (quantity * unit_price).quantize(CENT, rounding=ROUND_HALF_UP) != amount:
                raise ValueError("Line amount mismatch")
            subtotal += amount
            lines.append({
                "description": str(line["description"]),
                "quantity": str(quantity),
                "unit_price": f"{unit_price:.2f}",
                "amount": f"{amount:.2f}",
            })
        gst_rate = Decimal(str(invoice.gst_rate))
        if not gst_rate.is_finite() or gst_rate < 0:
            raise ValueError("Invalid tax rate")
        gst = _money(invoice.gst)
        total = _money(invoice.total)
        if subtotal != _money(invoice.subtotal) or (
            subtotal * gst_rate / Decimal("100")
        ).quantize(CENT, rounding=ROUND_HALF_UP) != gst or subtotal + gst != total:
            raise ValueError("Invoice totals mismatch")
    except (ValueError, KeyError, TypeError, InvalidOperation):
        blockers.append("Invoice lines, GST and total must reconcile exactly before export.")
        lines = []

    return QuickBooksInvoicePreview(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        customer_name=invoice.customer_name,
        project_id=invoice.project_id,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        status=invoice.status,
        subtotal=f"{_money(invoice.subtotal):.2f}",
        gst=f"{_money(invoice.gst):.2f}",
        total=f"{_money(invoice.total):.2f}",
        line_items=lines,
        source_checks_passed=not blockers,
        blockers=blockers,
        accounting_setup_required=[
            "Connect and verify the intended QuickBooks Online company.",
            "Match the customer and check for an existing QuickBooks invoice number.",
            "Approve the Canadian sales-tax, item and account mappings with the bookkeeper.",
            "Verify the final source PDF and authorize this exact accounting transfer.",
        ],
        export_enabled=False,
    )
