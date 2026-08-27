from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.field_operations import FieldRecord
from app.models.finance import CustomerInvoice
from app.models.project import Project, ProjectCloseoutChecklistItem
from app.schemas.finance import CustomerInvoiceCreate
from app.schemas.project_invoice_package import (
    ProjectInvoicePackageCreate,
    ProjectInvoicePackageReadiness,
    ProjectInvoicePackageResult,
    ProjectInvoiceSourceGroupRead,
    ProjectInvoiceSourceLineRead,
)
from app.services import customer_invoices
from app.services.auth import AuthenticatedUser
from app.services.finance import require_management
from app.services.projects import PROJECT_CLOSEOUT_CODES

MONEY = Decimal("0.01")


def get_readiness(
    db: Session,
    project_id: UUID,
    user: AuthenticatedUser,
) -> ProjectInvoicePackageReadiness:
    require_management(user)
    project = db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Project not found")
    closeout_items = _closeout_items(db, project_id)
    closeout_status, closeout_blockers = _closeout_status(closeout_items)
    project_blockers = []
    if project.status != "completed":
        project_blockers.append("Project status must be completed before a draft invoice package can be generated.")
    project_blockers.extend(closeout_blockers)

    records = list(
        db.scalars(
            select(FieldRecord)
            .where(
                FieldRecord.project_id == project_id,
                FieldRecord.record_type == "completed_work",
            )
            .order_by(FieldRecord.work_date, FieldRecord.created_at, FieldRecord.id)
        ).all()
    )
    grouped_records: dict[str, list[FieldRecord]] = defaultdict(list)
    missing_source_count = 0
    for record in records:
        source_import_key = str((record.details or {}).get("source_import_key") or "").strip()
        if not source_import_key:
            missing_source_count += 1
            continue
        grouped_records[source_import_key].append(record)
    if missing_source_count:
        project_blockers.append(
            f"{missing_source_count} completed-work source record(s) lack an exact source import key."
        )
    if not records:
        project_blockers.append("No completed-work source records are available for this project.")
    elif not grouped_records:
        project_blockers.append("No completed-work source group has a usable source import key.")

    groups = [
        _source_group(db, project_id, source_import_key, source_records)
        for source_import_key, source_records in sorted(grouped_records.items())
    ]
    ready = not project_blockers and any(group.ready for group in groups)
    return ProjectInvoicePackageReadiness(
        project_id=project.id,
        project_number=project.project_number,
        project_name=project.name,
        project_status=project.status,
        site_address=project.project_address,
        customer_reference=project.client_owner,
        closeout_status=closeout_status,
        ready=ready,
        blockers=project_blockers,
        groups=groups,
    )


def generate_package(
    db: Session,
    project_id: UUID,
    payload: ProjectInvoicePackageCreate,
    user: AuthenticatedUser,
) -> ProjectInvoicePackageResult:
    require_management(user)
    readiness = get_readiness(db, project_id, user)
    source_import_key = payload.source_import_key.strip()
    group = next(
        (item for item in readiness.groups if item.source_import_key == source_import_key),
        None,
    )
    if group is None:
        raise HTTPException(
            status_code=409,
            detail="The requested completed-work source group is not available for this project.",
        )
    if not group.ready:
        detail = group.blockers[0] if group.blockers else "Completed-work source group is not ready."
        raise HTTPException(status_code=409, detail=detail)

    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    source_record_ids = [str(line.id) for line in group.lines]
    package_key = _package_key(project_id, source_import_key)
    invoice_payload = CustomerInvoiceCreate(
        invoice_number=payload.invoice_number.strip(),
        project_id=project_id,
        project_name=project.name,
        site_address=project.project_address,
        customer_name=payload.customer_name.strip(),
        customer_address=payload.customer_address.strip(),
        customer_phone=(payload.customer_phone or "").strip() or None,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        terms=payload.terms.strip(),
        gst_rate=payload.gst_rate.strip(),
        line_items=[
            {
                "description": line.description,
                "quantity": line.quantity,
                "unit": line.unit,
                "unit_price": line.billable_rate,
            }
            for line in group.lines
        ],
    )
    calculated_values = customer_invoices._calculated_values(invoice_payload)
    existing = db.scalar(
        select(CustomerInvoice).where(CustomerInvoice.source_package_key == package_key)
    )
    if existing is not None:
        return _idempotent_result(
            existing,
            calculated_values,
            source_import_key,
            source_record_ids,
        )
    if not readiness.ready:
        detail = readiness.blockers[0] if readiness.blockers else "Project invoice package is not ready."
        raise HTTPException(status_code=409, detail=detail)
    duplicate_number = db.scalar(
        select(CustomerInvoice.id).where(
            CustomerInvoice.invoice_number == invoice_payload.invoice_number
        )
    )
    if duplicate_number is not None:
        raise HTTPException(status_code=409, detail="Invoice number already exists")

    closeout_snapshot = _closeout_snapshot(db, project_id)
    generated_at = datetime.now(UTC)
    invoice = CustomerInvoice(
        **calculated_values,
        status="draft",
        source_package_key=package_key,
        source_import_key=source_import_key,
        source_record_ids_json=source_record_ids,
        closeout_snapshot_json=closeout_snapshot,
        package_generated_by=user.email,
        package_generated_at=generated_at,
        created_by=user.email,
    )
    db.add(invoice)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        concurrent = db.scalar(
            select(CustomerInvoice).where(CustomerInvoice.source_package_key == package_key)
        )
        if concurrent is not None:
            return _idempotent_result(
                concurrent,
                calculated_values,
                source_import_key,
                source_record_ids,
            )
        raise HTTPException(
            status_code=409,
            detail="Invoice package conflicts with an existing invoice or package.",
        ) from exc
    db.refresh(invoice)
    return ProjectInvoicePackageResult(
        invoice=customer_invoices._read(invoice),
        created=True,
        idempotent=False,
        generated_at=invoice.package_generated_at or generated_at,
    )


def _closeout_items(db: Session, project_id: UUID) -> list[ProjectCloseoutChecklistItem]:
    return list(
        db.scalars(
            select(ProjectCloseoutChecklistItem)
            .where(ProjectCloseoutChecklistItem.project_id == project_id)
            .order_by(ProjectCloseoutChecklistItem.sort_order)
        ).all()
    )


def _closeout_status(
    items: list[ProjectCloseoutChecklistItem],
) -> tuple[str, list[str]]:
    if not items:
        return "missing", ["Project closeout controls have not been initialized."]
    if {item.code for item in items} != PROJECT_CLOSEOUT_CODES:
        return "not_ready", ["Project closeout controls do not match the required control set."]
    incomplete = [
        item for item in items if not item.completed or not str(item.evidence or "").strip()
    ]
    if incomplete:
        return "not_ready", [
            f"{len(incomplete)} project closeout control(s) still require completion evidence."
        ]
    return "ready", []


def _closeout_snapshot(db: Session, project_id: UUID) -> dict:
    items = _closeout_items(db, project_id)
    status, blockers = _closeout_status(items)
    if status != "ready":
        raise HTTPException(status_code=409, detail=blockers[0])
    return {
        "status": "ready",
        "captured_at": datetime.now(UTC).isoformat(),
        "controls": [
            {
                "code": item.code,
                "category": item.category,
                "label": item.label,
                "sort_order": item.sort_order,
                "completed": item.completed,
                "evidence": item.evidence,
                "changed_by": item.changed_by,
                "changed_at": item.changed_at.isoformat() if item.changed_at else None,
            }
            for item in items
        ],
    }


def _source_group(
    db: Session,
    project_id: UUID,
    source_import_key: str,
    records: list[FieldRecord],
) -> ProjectInvoiceSourceGroupRead:
    blockers: list[str] = []
    lines: list[ProjectInvoiceSourceLineRead] = []
    source_line_keys: set[str] = set()
    source_invoice_numbers: set[str] = set()
    source_drive_file_ids: set[str] = set()
    source_invoice_dates: set[date] = set()
    subtotal = Decimal("0")
    ordered_records = sorted(
        records,
        key=lambda record: (
            record.work_date,
            _source_position((record.details or {}).get("source_line_position")),
            str((record.details or {}).get("source_line_key") or ""),
            str(record.id),
        ),
    )
    for record in ordered_records:
        details = record.details or {}
        source_line_key = str(details.get("source_line_key") or "").strip()
        description = str(details.get("description") or "").strip()
        unit = str(details.get("unit") or "").strip()
        if not source_line_key:
            blockers.append(f"Source record {record.id} lacks a source line key.")
        elif source_line_key in source_line_keys:
            blockers.append(f"Source line key {source_line_key} is duplicated in this source group.")
        else:
            source_line_keys.add(source_line_key)
        if not description:
            blockers.append(f"Source record {record.id} lacks a completed-work description.")
        elif len(description) > 500:
            blockers.append(f"Source record {record.id} description exceeds the invoice line limit.")
        if not unit:
            blockers.append(f"Source record {record.id} lacks a unit.")
        elif len(unit) > 30:
            blockers.append(f"Source record {record.id} unit exceeds the invoice line limit.")
        quantity = _source_decimal(details.get("quantity"), "quantity", record.id, blockers)
        rate = _source_decimal(details.get("billable_rate"), "billable rate", record.id, blockers)
        amount = _source_decimal(details.get("billable_amount"), "billable amount", record.id, blockers)
        if quantity is not None and quantity <= 0:
            blockers.append(f"Source record {record.id} quantity must be greater than zero.")
        elif quantity is not None and len(str(quantity)) > 30:
            blockers.append(f"Source record {record.id} quantity exceeds the invoice line limit.")
        if rate is not None and rate < 0:
            blockers.append(f"Source record {record.id} billable rate cannot be negative.")
        elif rate is not None and len(f"{rate.quantize(MONEY, rounding=ROUND_HALF_UP):.2f}") > 30:
            blockers.append(f"Source record {record.id} billable rate exceeds the invoice line limit.")
        if amount is not None and amount < 0:
            blockers.append(f"Source record {record.id} billable amount cannot be negative.")
        expected_amount = None
        if quantity is not None and rate is not None:
            expected_amount = (quantity * rate).quantize(MONEY, rounding=ROUND_HALF_UP)
        if expected_amount is not None and amount is not None and amount != expected_amount:
            blockers.append(
                f"Source record {record.id} amount does not equal its source quantity multiplied by rate."
            )
        source_invoice_number = str(details.get("source_invoice_number") or "").strip() or None
        source_drive_file_id = str(details.get("source_drive_file_id") or "").strip() or None
        source_invoice_date = _source_date(details.get("source_invoice_date"), record.id, blockers)
        if source_invoice_number:
            source_invoice_numbers.add(source_invoice_number)
        if source_drive_file_id:
            source_drive_file_ids.add(source_drive_file_id)
        if source_invoice_date:
            source_invoice_dates.add(source_invoice_date)
        if (
            source_line_key
            and description
            and unit
            and quantity is not None
            and rate is not None
            and amount is not None
        ):
            subtotal += amount
            lines.append(
                ProjectInvoiceSourceLineRead(
                    id=record.id,
                    work_date=record.work_date,
                    source_line_key=source_line_key,
                    source_invoice_number=source_invoice_number,
                    description=description,
                    quantity=str(quantity),
                    unit=unit,
                    billable_rate=f"{rate.quantize(MONEY, rounding=ROUND_HALF_UP):.2f}",
                    billable_amount=f"{amount.quantize(MONEY, rounding=ROUND_HALF_UP):.2f}",
                )
            )
    if len(source_invoice_numbers) > 1:
        blockers.append("Source invoice number is inconsistent within this source group.")
    if len(source_drive_file_ids) > 1:
        blockers.append("Source Drive file is inconsistent within this source group.")
    if len(source_invoice_dates) > 1:
        blockers.append("Source invoice date is inconsistent within this source group.")
    if len(lines) != len(records):
        blockers.append("Every source record must produce one complete invoice line.")

    package_key = _package_key(project_id, source_import_key)
    existing = db.scalar(
        select(CustomerInvoice).where(CustomerInvoice.source_package_key == package_key)
    )
    return ProjectInvoiceSourceGroupRead(
        source_import_key=source_import_key,
        source_invoice_number=(
            next(iter(source_invoice_numbers)) if len(source_invoice_numbers) == 1 else None
        ),
        source_drive_file_id=(
            next(iter(source_drive_file_ids)) if len(source_drive_file_ids) == 1 else None
        ),
        source_invoice_date=(
            next(iter(source_invoice_dates)) if len(source_invoice_dates) == 1 else None
        ),
        line_count=len(records),
        subtotal=f"{subtotal.quantize(MONEY, rounding=ROUND_HALF_UP):.2f}",
        ready=not blockers,
        blockers=list(dict.fromkeys(blockers)),
        lines=lines,
        existing_invoice_id=existing.id if existing else None,
        existing_invoice_number=existing.invoice_number if existing else None,
        existing_invoice_status=existing.status if existing else None,
    )


def _source_decimal(
    value: object,
    label: str,
    record_id: UUID,
    blockers: list[str],
) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        blockers.append(f"Source record {record_id} has an invalid {label}.")
        return None
    if not parsed.is_finite():
        blockers.append(f"Source record {record_id} has a non-finite {label}.")
        return None
    return parsed


def _source_position(value: object) -> int:
    try:
        position = int(str(value))
    except (TypeError, ValueError):
        return 2_147_483_647
    return position if position >= 0 else 2_147_483_647


def _source_date(value: object, record_id: UUID, blockers: list[str]) -> date | None:
    if value in {None, ""}:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        blockers.append(f"Source record {record_id} has an invalid source invoice date.")
        return None


def _package_key(project_id: UUID, source_import_key: str) -> str:
    digest = sha256(f"{project_id}:{source_import_key}".encode()).hexdigest()
    return f"completed-work:{digest}"


def _idempotent_result(
    invoice: CustomerInvoice,
    calculated_values: dict,
    source_import_key: str,
    source_record_ids: list[str],
) -> ProjectInvoicePackageResult:
    comparable_fields = (
        "invoice_number",
        "project_id",
        "project_name",
        "site_address",
        "customer_name",
        "customer_address",
        "customer_phone",
        "invoice_date",
        "due_date",
        "terms",
        "line_items_json",
    )
    same = all(getattr(invoice, field) == calculated_values[field] for field in comparable_fields)
    same = same and Decimal(invoice.gst_rate) == Decimal(calculated_values["gst_rate"])
    same = same and invoice.source_import_key == source_import_key
    same = same and invoice.source_record_ids_json == source_record_ids
    if not same:
        raise HTTPException(
            status_code=409,
            detail="This completed-work source group already has a different invoice package.",
        )
    generated_at = invoice.package_generated_at or invoice.created_at
    return ProjectInvoicePackageResult(
        invoice=customer_invoices._read(invoice),
        created=False,
        idempotent=True,
        generated_at=generated_at,
    )
