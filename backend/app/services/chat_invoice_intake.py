from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.finance import CustomerInvoice
from app.models.project import Project
from app.schemas.chat_invoice_intake import (
    ChatInvoiceIntakeItemResult,
    ChatInvoiceIntakeRecord,
    ChatInvoiceIntakeRequest,
    ChatInvoiceIntakeResponse,
)
from app.schemas.finance import CustomerInvoiceCreate
from app.services import customer_invoices
from app.services.auth import AuthenticatedUser
from app.services.finance import require_management


def import_chat_invoices(
    db: Session,
    payload: ChatInvoiceIntakeRequest,
    user: AuthenticatedUser,
) -> ChatInvoiceIntakeResponse:
    require_management(user)
    results = [_import_record(db, record, user) for record in payload.items]
    return ChatInvoiceIntakeResponse(
        items=results,
        created_count=sum(item.status == "created" for item in results),
        reused_count=sum(item.status == "reused" for item in results),
        conflict_count=sum(item.status == "conflict" for item in results),
        error_count=sum(item.status == "error" for item in results),
    )


def _import_record(
    db: Session,
    record: ChatInvoiceIntakeRecord,
    user: AuthenticatedUser,
) -> ChatInvoiceIntakeItemResult:
    invoice_number = record.invoice.invoice_number

    # Check idempotency before resolving or creating a project so retries cannot
    # create project side effects before discovering an existing invoice.
    existing = _find_invoice(db, invoice_number)
    if existing is not None:
        return _existing_invoice_result(existing, record.invoice)

    try:
        project, project_created = _resolve_project(db, record)
    except HTTPException as exc:
        db.rollback()
        return ChatInvoiceIntakeItemResult(
            invoice_number=invoice_number,
            status="error" if exc.status_code != 409 else "conflict",
            detail=str(exc.detail),
        )

    linked_payload = record.invoice.model_copy(
        update={"project_id": project.id if project is not None else record.invoice.project_id}
    )
    values = customer_invoices._calculated_values(linked_payload)
    invoice_row = CustomerInvoice(**values, status="draft", created_by=user.email)
    db.add(invoice_row)

    try:
        # Project creation and invoice creation commit together. If a concurrent
        # request wins the unique invoice-number race, both are rolled back here.
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _find_invoice(db, invoice_number)
        if existing is not None:
            return _existing_invoice_result(existing, record.invoice)
        return ChatInvoiceIntakeItemResult(
            invoice_number=invoice_number,
            status="error",
            detail="Invoice intake conflicted with another database write. Retry safely.",
        )

    db.refresh(invoice_row)
    invoice = customer_invoices._read(invoice_row)
    return ChatInvoiceIntakeItemResult(
        invoice_number=invoice_number,
        status="created",
        project_id=project.id if project is not None else invoice.project_id,
        project_created=project_created,
        invoice=invoice,
    )


def _find_invoice(db: Session, invoice_number: str) -> CustomerInvoice | None:
    return db.scalar(
        select(CustomerInvoice).where(CustomerInvoice.invoice_number == invoice_number)
    )


def _existing_invoice_result(
    existing: CustomerInvoice,
    payload: CustomerInvoiceCreate,
) -> ChatInvoiceIntakeItemResult:
    # When no explicit project ID was supplied, compare against the project that
    # is already linked to the existing invoice. This makes a retry of an intake
    # that originally created its project idempotent without creating a new one.
    comparison_payload = payload
    if payload.project_id is None:
        comparison_payload = payload.model_copy(update={"project_id": existing.project_id})

    if _invoice_matches(existing, comparison_payload):
        return ChatInvoiceIntakeItemResult(
            invoice_number=existing.invoice_number,
            status="reused",
            project_id=existing.project_id,
            project_created=False,
            invoice=customer_invoices._read(existing),
            detail="Invoice already exists with identical intake data.",
        )
    return ChatInvoiceIntakeItemResult(
        invoice_number=existing.invoice_number,
        status="conflict",
        project_id=existing.project_id,
        project_created=False,
        detail="Invoice number already exists with different data.",
    )


def _resolve_project(
    db: Session,
    record: ChatInvoiceIntakeRecord,
) -> tuple[Project | None, bool]:
    payload = record.invoice
    if payload.project_id is not None:
        project = db.get(Project, payload.project_id)
        if project is None or project.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project, False

    project_name = payload.project_name.strip()
    site_address = payload.site_address.strip() if payload.site_address else None
    statement = select(Project).where(
        Project.deleted_at.is_(None),
        func.lower(Project.name) == project_name.lower(),
    )
    if site_address:
        statement = statement.where(func.lower(Project.project_address) == site_address.lower())
    matches = list(db.scalars(statement).all())
    if len(matches) > 1:
        raise HTTPException(
            status_code=409,
            detail="Multiple projects match the supplied project name/site address.",
        )
    if matches:
        return matches[0], False
    if not record.create_project_if_missing:
        return None, False

    created = Project(
        name=project_name,
        client_owner=payload.customer_name.strip(),
        project_address=site_address,
        status=record.project_status.value,
        notes="Created from management chat invoice intake.",
        metadata_json={},
    )
    db.add(created)
    db.flush()
    return created, True


def _invoice_matches(existing: CustomerInvoice, payload: CustomerInvoiceCreate) -> bool:
    calculated = customer_invoices._calculated_values(payload)
    return all(
        (
            existing.project_id == calculated.get("project_id"),
            existing.project_name == calculated.get("project_name"),
            existing.site_address == calculated.get("site_address"),
            existing.customer_name == calculated.get("customer_name"),
            existing.customer_address == calculated.get("customer_address"),
            existing.customer_phone == calculated.get("customer_phone"),
            existing.invoice_date == calculated.get("invoice_date"),
            existing.due_date == calculated.get("due_date"),
            existing.terms == calculated.get("terms"),
            existing.line_items_json == calculated.get("line_items_json"),
            Decimal(existing.gst_rate) == Decimal(calculated.get("gst_rate")),
            Decimal(existing.subtotal) == Decimal(calculated.get("subtotal")),
            Decimal(existing.gst) == Decimal(calculated.get("gst")),
            Decimal(existing.total) == Decimal(calculated.get("total")),
        )
    )
