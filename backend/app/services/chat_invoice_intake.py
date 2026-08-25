from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
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
from app.schemas.project import ProjectCreate
from app.services import customer_invoices, projects
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
    try:
        project, project_created = _resolve_project(db, record)
    except HTTPException as exc:
        return ChatInvoiceIntakeItemResult(
            invoice_number=invoice_number,
            status="error" if exc.status_code != 409 else "conflict",
            detail=str(exc.detail),
        )

    linked_payload = record.invoice.model_copy(
        update={"project_id": project.id if project is not None else record.invoice.project_id}
    )
    existing = db.scalar(
        select(CustomerInvoice).where(CustomerInvoice.invoice_number == invoice_number)
    )
    if existing is not None:
        if _invoice_matches(existing, linked_payload):
            return ChatInvoiceIntakeItemResult(
                invoice_number=invoice_number,
                status="reused",
                project_id=existing.project_id,
                project_created=project_created,
                invoice=customer_invoices._read(existing),
                detail="Invoice already exists with identical intake data.",
            )
        return ChatInvoiceIntakeItemResult(
            invoice_number=invoice_number,
            status="conflict",
            project_id=project.id if project is not None else existing.project_id,
            project_created=project_created,
            detail="Invoice number already exists with different data.",
        )

    try:
        invoice = customer_invoices.create_invoice(db, linked_payload, user)
    except HTTPException as exc:
        return ChatInvoiceIntakeItemResult(
            invoice_number=invoice_number,
            status="error" if exc.status_code != 409 else "conflict",
            project_id=project.id if project is not None else None,
            project_created=project_created,
            detail=str(exc.detail),
        )
    return ChatInvoiceIntakeItemResult(
        invoice_number=invoice_number,
        status="created",
        project_id=project.id if project is not None else invoice.project_id,
        project_created=project_created,
        invoice=invoice,
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

    statement = select(Project).where(
        Project.deleted_at.is_(None),
        func.lower(Project.name) == payload.project_name.strip().lower(),
    )
    if payload.site_address:
        statement = statement.where(
            func.lower(Project.project_address) == payload.site_address.strip().lower()
        )
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

    created = projects.create_project(
        db,
        ProjectCreate(
            name=payload.project_name,
            client_owner=payload.customer_name,
            project_address=payload.site_address,
            status=record.project_status,
            notes="Created from management chat invoice intake.",
        ),
    )
    return db.get(Project, created.id), True


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
