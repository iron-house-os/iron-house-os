import re
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.customer_quote import CustomerQuote
from app.models.project import Project
from app.schemas.customer_quote import (
    CustomerQuoteAccept,
    CustomerQuoteCreate,
    CustomerQuoteLineItem,
    CustomerQuoteList,
    CustomerQuoteRead,
    CustomerQuoteStatus,
    CustomerQuoteStatusUpdate,
    CustomerQuoteUpdate,
)
from app.schemas.project import ProjectStatus
from app.services import projects

QUOTE_NUMBER_PREFIX = "Q"
QUOTE_NUMBER_WIDTH = 3
QUOTE_NUMBER_RETRY_LIMIT = 20
MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _line_items(items: list[CustomerQuoteLineItem]) -> tuple[list[dict], Decimal]:
    normalized: list[dict] = []
    subtotal = Decimal("0")
    for item in items:
        amount = _money(item.quantity * item.unit_price)
        subtotal += amount
        normalized.append(
            {
                "description": item.description.strip(),
                "quantity": str(item.quantity),
                "unit": item.unit.strip(),
                "unit_price": str(_money(item.unit_price)),
                "amount": str(amount),
            }
        )
    return normalized, _money(subtotal)


def _totals(items: list[CustomerQuoteLineItem], gst_rate: Decimal) -> tuple[list[dict], Decimal, Decimal, Decimal]:
    normalized, subtotal = _line_items(items)
    gst = _money(subtotal * gst_rate / Decimal("100"))
    return normalized, subtotal, gst, _money(subtotal + gst)


def _clean_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _next_quote_number(db: Session) -> str:
    year = datetime.now(projects.IRON_HOUSE_TIME_ZONE).year
    prefix = f"{QUOTE_NUMBER_PREFIX}-{year}-"
    existing = db.scalars(
        select(CustomerQuote.quote_number).where(CustomerQuote.quote_number.like(f"{prefix}%"))
    ).all()
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    sequences = [
        int(match.group(1))
        for number in existing
        if number and (match := pattern.match(number))
    ]
    return f"{prefix}{max(sequences, default=0) + 1:0{QUOTE_NUMBER_WIDTH}d}"


def _load_quote(db: Session, quote_id: UUID, *, for_update: bool = False) -> CustomerQuote:
    statement = select(CustomerQuote).where(CustomerQuote.id == quote_id)
    if for_update:
        statement = statement.with_for_update()
    quote = db.scalar(statement)
    if quote is None:
        raise AppError("Customer quote not found.", status_code=404)
    return quote


def _load_project(db: Session, project_id: UUID, *, for_update: bool = False) -> Project:
    statement = select(Project).where(Project.id == project_id)
    if for_update:
        statement = statement.with_for_update()
    project = db.scalar(statement)
    if project is None:
        raise AppError("Project not found.", status_code=404)
    return project


def _read(quote: CustomerQuote, project: Project) -> CustomerQuoteRead:
    return CustomerQuoteRead(
        id=quote.id,
        project_id=quote.project_id,
        project_name=project.name,
        quote_number=quote.quote_number,
        customer_name=quote.customer_name,
        customer_email=quote.customer_email,
        customer_phone=quote.customer_phone,
        site_address=quote.site_address,
        scope_summary=quote.scope_summary,
        line_items=quote.line_items_json,
        assumptions=quote.assumptions_json,
        exclusions=quote.exclusions_json,
        subtotal=quote.subtotal,
        gst_rate=quote.gst_rate,
        gst=quote.gst,
        total=quote.total,
        quote_date=quote.quote_date,
        valid_until=quote.valid_until,
        status=quote.status,
        record_revision=quote.record_revision,
        notes=quote.notes,
        created_by=quote.created_by,
        sent_at=quote.sent_at,
        accepted_at=quote.accepted_at,
        accepted_by=quote.accepted_by,
        acceptance_reference=quote.acceptance_reference,
        acceptance_note=quote.acceptance_note,
        closed_at=quote.closed_at,
        job_number=project.project_number,
        created_at=quote.created_at,
        updated_at=quote.updated_at,
    )


def create_customer_quote(
    db: Session,
    payload: CustomerQuoteCreate,
    actor_email: str,
) -> CustomerQuoteRead:
    line_items, subtotal, gst, total = _totals(payload.line_items, payload.gst_rate)
    for _ in range(QUOTE_NUMBER_RETRY_LIMIT):
        try:
            if payload.project_id:
                project = _load_project(db, payload.project_id)
                if project.status == ProjectStatus.archived.value:
                    raise AppError("Archived projects cannot receive quotes.", status_code=409)
            else:
                project = Project(
                    name=payload.project_name.strip(),
                    client_owner=payload.customer_name.strip(),
                    project_address=payload.site_address.strip() if payload.site_address else None,
                    description=payload.scope_summary.strip(),
                    contract_value=total,
                    status=ProjectStatus.opportunity.value,
                    metadata_json={"source": "customer_quote"},
                )
                db.add(project)
                db.flush()

            quote = CustomerQuote(
                project_id=project.id,
                quote_number=_next_quote_number(db),
                customer_name=payload.customer_name.strip(),
                customer_email=payload.customer_email.strip() if payload.customer_email else None,
                customer_phone=payload.customer_phone.strip() if payload.customer_phone else None,
                site_address=payload.site_address.strip() if payload.site_address else None,
                scope_summary=payload.scope_summary.strip(),
                line_items_json=line_items,
                assumptions_json=_clean_list(payload.assumptions),
                exclusions_json=_clean_list(payload.exclusions),
                subtotal=subtotal,
                gst_rate=payload.gst_rate,
                gst=gst,
                total=total,
                quote_date=payload.quote_date,
                valid_until=payload.valid_until,
                status=CustomerQuoteStatus.draft.value,
                record_revision=1,
                notes=payload.notes.strip() if payload.notes else None,
                created_by=actor_email,
            )
            db.add(quote)
            db.commit()
            db.refresh(quote)
            db.refresh(project)
            return _read(quote, project)
        except IntegrityError:
            db.rollback()
            continue
    raise AppError("Unable to allocate a unique quote number. Try again.", status_code=409)


def list_customer_quotes(db: Session, quote_status: str | None = None) -> CustomerQuoteList:
    statement = select(CustomerQuote).order_by(CustomerQuote.updated_at.desc())
    if quote_status:
        statement = statement.where(CustomerQuote.status == quote_status)
    quotes = list(db.scalars(statement).all())
    projects_by_id = {
        project.id: project
        for project in db.scalars(
            select(Project).where(Project.id.in_({quote.project_id for quote in quotes}))
        ).all()
    } if quotes else {}
    items = [_read(quote, projects_by_id[quote.project_id]) for quote in quotes]
    return CustomerQuoteList(items=items, total=len(items))


def get_customer_quote(db: Session, quote_id: UUID) -> CustomerQuoteRead:
    quote = _load_quote(db, quote_id)
    return _read(quote, _load_project(db, quote.project_id))


def update_customer_quote(
    db: Session,
    quote_id: UUID,
    payload: CustomerQuoteUpdate,
) -> CustomerQuoteRead:
    quote = _load_quote(db, quote_id, for_update=True)
    if quote.status == CustomerQuoteStatus.accepted.value:
        raise AppError("Accepted quotes are immutable.", status_code=409)
    if quote.record_revision != payload.expected_revision:
        raise AppError("This quote changed in another session. Reload before saving.", status_code=409)

    direct_fields = (
        "customer_name",
        "customer_email",
        "customer_phone",
        "site_address",
        "scope_summary",
        "quote_date",
        "valid_until",
        "notes",
    )
    for field in direct_fields:
        if field in payload.model_fields_set:
            value = getattr(payload, field)
            if field in {"customer_name", "scope_summary"} and value is None:
                continue
            if isinstance(value, str):
                value = value.strip() or None
            setattr(quote, field, value)
    if payload.assumptions is not None:
        quote.assumptions_json = _clean_list(payload.assumptions)
    if payload.exclusions is not None:
        quote.exclusions_json = _clean_list(payload.exclusions)

    line_items = None
    if payload.line_items is not None:
        line_items = payload.line_items
    gst_rate = payload.gst_rate if payload.gst_rate is not None else quote.gst_rate
    if line_items is not None:
        normalized, subtotal, gst, total = _totals(line_items, gst_rate)
        quote.line_items_json = normalized
        quote.subtotal = subtotal
        quote.gst = gst
        quote.total = total
    elif payload.gst_rate is not None:
        quote.gst = _money(quote.subtotal * gst_rate / Decimal("100"))
        quote.total = _money(quote.subtotal + quote.gst)
    quote.gst_rate = gst_rate
    if quote.status in {CustomerQuoteStatus.declined.value, CustomerQuoteStatus.expired.value}:
        quote.status = CustomerQuoteStatus.draft.value
        quote.closed_at = None
    quote.record_revision += 1

    project = _load_project(db, quote.project_id, for_update=True)
    if payload.project_name is not None:
        project.name = payload.project_name.strip()
    project.client_owner = quote.customer_name
    project.project_address = quote.site_address
    project.description = quote.scope_summary
    project.contract_value = quote.total
    db.commit()
    db.refresh(quote)
    db.refresh(project)
    return _read(quote, project)


def update_customer_quote_status(
    db: Session,
    quote_id: UUID,
    payload: CustomerQuoteStatusUpdate,
) -> CustomerQuoteRead:
    if payload.status not in {
        CustomerQuoteStatus.sent,
        CustomerQuoteStatus.declined,
        CustomerQuoteStatus.expired,
    }:
        raise AppError("Use the acceptance action to accept a quote.", status_code=422)
    quote = _load_quote(db, quote_id, for_update=True)
    if quote.status == CustomerQuoteStatus.accepted.value:
        raise AppError("Accepted quotes are immutable.", status_code=409)
    if quote.status in {CustomerQuoteStatus.declined.value, CustomerQuoteStatus.expired.value}:
        raise AppError("Create a new quote revision before reopening a closed quote.", status_code=409)
    if quote.record_revision != payload.expected_revision:
        raise AppError("This quote changed in another session. Reload before saving.", status_code=409)
    now = datetime.now(UTC)
    quote.status = payload.status.value
    quote.record_revision += 1
    if payload.note:
        quote.notes = payload.note.strip()
    if payload.status == CustomerQuoteStatus.sent:
        quote.sent_at = now
        quote.closed_at = None
    else:
        quote.closed_at = now
    db.commit()
    project = _load_project(db, quote.project_id)
    db.refresh(quote)
    return _read(quote, project)


def accept_customer_quote(
    db: Session,
    quote_id: UUID,
    payload: CustomerQuoteAccept,
    actor_email: str,
) -> CustomerQuoteRead:
    for _ in range(projects.JOB_NUMBER_RETRY_LIMIT):
        quote = _load_quote(db, quote_id, for_update=True)
        project = _load_project(db, quote.project_id, for_update=True)
        if quote.status == CustomerQuoteStatus.accepted.value:
            return _read(quote, project)
        if quote.record_revision != payload.expected_revision:
            raise AppError("This quote changed in another session. Reload before accepting.", status_code=409)
        if quote.status in {CustomerQuoteStatus.declined.value, CustomerQuoteStatus.expired.value}:
            raise AppError("Closed quotes cannot be accepted without a new revision.", status_code=409)

        now = datetime.now(UTC)
        quote.status = CustomerQuoteStatus.accepted.value
        quote.record_revision += 1
        quote.accepted_at = now
        quote.accepted_by = actor_email
        quote.acceptance_reference = payload.acceptance_reference.strip()
        quote.acceptance_note = payload.acceptance_note.strip() if payload.acceptance_note else None
        quote.closed_at = now
        project.client_owner = quote.customer_name
        project.project_address = quote.site_address
        project.description = quote.scope_summary
        project.contract_value = quote.total
        try:
            projects.prepare_project_award(db, project)
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(quote)
        db.refresh(project)
        return _read(quote, project)
    raise AppError("Unable to allocate a unique job number. Try again.", status_code=409)
