from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.field_operations import FieldRecord
from app.models.finance import FinancialEntry
from app.models.project import Project
from app.schemas.finance import (
    CompletedWorkCostCreate,
    CompletedWorkCostCreateResult,
    CompletedWorkCostLedger,
    CompletedWorkCostLine,
    FinancialEntryRead,
)
from app.services.auth import AuthenticatedUser
from app.services.finance import require_management


SOURCE_TYPE = "completed_work_actual"
MONEY = Decimal("0.01")
REVENUE_COST_WARNING = (
    "Billable quantities, rates, and amounts are revenue evidence only. Linked entries are explicit internal actual costs; "
    "this view does not prove that every project cost is captured or that project margin is complete."
)


def get_ledger(
    db: Session,
    project_id: UUID,
    user: AuthenticatedUser,
) -> CompletedWorkCostLedger:
    require_management(user)
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    records = list(
        db.scalars(
            select(FieldRecord)
            .where(
                FieldRecord.project_id == project_id,
                FieldRecord.record_type == "completed_work",
            )
            .order_by(FieldRecord.work_date.asc(), FieldRecord.created_at.asc())
        )
    )
    record_ids = [record.id for record in records]
    entries = (
        list(
            db.scalars(
                select(FinancialEntry)
                .where(
                    FinancialEntry.project_id == project_id,
                    FinancialEntry.source_type == SOURCE_TYPE,
                    FinancialEntry.source_id.in_(record_ids),
                    FinancialEntry.entry_type == "actual",
                    FinancialEntry.status != "void",
                )
                .order_by(FinancialEntry.entry_date.asc(), FinancialEntry.created_at.asc())
            )
        )
        if record_ids
        else []
    )
    entries_by_record: dict[UUID, list[FinancialEntry]] = {record_id: [] for record_id in record_ids}
    for entry in entries:
        if entry.source_id in entries_by_record:
            entries_by_record[entry.source_id].append(entry)

    lines: list[CompletedWorkCostLine] = []
    for record in records:
        details = record.details or {}
        linked_entries = entries_by_record[record.id]
        lines.append(
            CompletedWorkCostLine(
                id=record.id,
                work_date=record.work_date,
                source_import_key=str(details.get("source_import_key") or ""),
                source_line_key=str(details.get("source_line_key") or ""),
                source_invoice_number=_optional_text(details.get("source_invoice_number")),
                source_drive_file_id=_optional_text(details.get("source_drive_file_id")),
                description=str(details.get("description") or record.title),
                quantity=str(details.get("quantity") or ""),
                unit=str(details.get("unit") or ""),
                billable_rate=str(details.get("billable_rate") or ""),
                billable_amount=str(details.get("billable_amount") or ""),
                internal_cost_status=str(details.get("cost_status") or "internal_cost_unverified"),
                linked_actual_cost_total=_sum(linked_entries),
                linked_entries=[FinancialEntryRead.model_validate(entry) for entry in linked_entries],
            )
        )

    linked_line_count = sum(1 for line in lines if line.linked_entries)
    return CompletedWorkCostLedger(
        project_id=project.id,
        project_name=project.name,
        source_line_count=len(lines),
        linked_line_count=linked_line_count,
        unlinked_line_count=len(lines) - linked_line_count,
        linked_actual_cost_total=_sum(entries),
        warning=REVENUE_COST_WARNING,
        lines=lines,
    )


def create_cost(
    db: Session,
    project_id: UUID,
    payload: CompletedWorkCostCreate,
    user: AuthenticatedUser,
) -> CompletedWorkCostCreateResult:
    require_management(user)
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    record = db.get(FieldRecord, payload.completed_work_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Completed-work record not found")
    if record.record_type != "completed_work":
        raise HTTPException(status_code=400, detail="The selected source is not a completed-work record.")
    if record.project_id != project_id:
        raise HTTPException(status_code=400, detail="The completed-work record must belong to the selected project.")

    source_key = str(payload.idempotency_key)
    existing = _find_by_source_key(db, record.id, source_key)
    if existing is not None:
        _verify_exact_retry(existing, project_id, payload)
        return CompletedWorkCostCreateResult(
            entry=FinancialEntryRead.model_validate(existing),
            created=False,
            idempotent=True,
        )

    details = record.details or {}
    entry = FinancialEntry(
        project_id=project_id,
        cost_code=payload.cost_code,
        entry_type="actual",
        category=payload.category,
        amount=payload.amount,
        entry_date=payload.entry_date,
        vendor_name=payload.vendor_name,
        reference=payload.reference,
        description=payload.description,
        source_type=SOURCE_TYPE,
        source_id=record.id,
        source_key=source_key,
        status="posted",
        metadata_json={
            "idempotency_key": source_key,
            "completed_work_id": str(record.id),
            "source_import_key": str(details.get("source_import_key") or ""),
            "source_line_key": str(details.get("source_line_key") or ""),
            "source_invoice_number": _optional_text(details.get("source_invoice_number")),
            "source_drive_file_id": _optional_text(details.get("source_drive_file_id")),
            "revenue_trace_only": True,
            "billable_values_not_used_as_cost": True,
        },
        created_by=user.email,
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        concurrent = _find_by_source_key(db, record.id, source_key)
        if concurrent is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The completed-work cost could not be saved because of a concurrent change.",
            ) from exc
        _verify_exact_retry(concurrent, project_id, payload)
        return CompletedWorkCostCreateResult(
            entry=FinancialEntryRead.model_validate(concurrent),
            created=False,
            idempotent=True,
        )
    db.refresh(entry)
    return CompletedWorkCostCreateResult(
        entry=FinancialEntryRead.model_validate(entry),
        created=True,
        idempotent=False,
    )


def _find_by_source_key(db: Session, record_id: UUID, source_key: str) -> FinancialEntry | None:
    return db.scalar(
        select(FinancialEntry).where(
            FinancialEntry.source_type == SOURCE_TYPE,
            FinancialEntry.source_id == record_id,
            FinancialEntry.source_key == source_key,
        )
    )


def _verify_exact_retry(
    entry: FinancialEntry,
    project_id: UUID,
    payload: CompletedWorkCostCreate,
) -> None:
    expected = {
        "project_id": project_id,
        "cost_code": payload.cost_code,
        "entry_type": "actual",
        "category": payload.category,
        "amount": _money(payload.amount),
        "entry_date": payload.entry_date,
        "vendor_name": payload.vendor_name,
        "reference": payload.reference,
        "description": payload.description,
        "status": "posted",
    }
    actual = {
        **{key: getattr(entry, key) for key in expected if key != "amount"},
        "amount": _money(entry.amount),
    }
    if actual != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That idempotency key already exists with different completed-work cost content; manual review is required.",
        )


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _sum(entries: list[FinancialEntry]) -> float:
    return float(sum((_money(entry.amount) for entry in entries), Decimal("0.00")))


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
