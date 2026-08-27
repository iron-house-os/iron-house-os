import hashlib
import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.bid import Bid
from app.models.customer_quote import CustomerQuote
from app.models.document import Document
from app.models.project import Project
from app.schemas.customer_quote import (
    CustomerQuoteAccept,
    CustomerQuoteCreate,
    CustomerQuoteIssueStatus,
    CustomerQuoteIssueUpdate,
    CustomerQuoteLineItem,
    CustomerQuoteList,
    CustomerQuoteRead,
    CustomerQuoteStatus,
    CustomerQuoteStatusUpdate,
    CustomerQuoteUpdate,
)
from app.schemas.estimate import EstimateSummary
from app.schemas.project import ProjectStatus
from app.services import projects

QUOTE_NUMBER_PREFIX = "Q"
QUOTE_NUMBER_WIDTH = 3
QUOTE_NUMBER_RETRY_LIMIT = 20
MONEY = Decimal("0.01")

PROCUREMENT_RULES = (
    ("rental", ("rental", "rent ", "roller", "skid steer", "excavator", "cutoff saw", "cut-off saw")),
    ("trucking", ("trucking", "tandem", "haul", "disposal", "dump fee", "delivery")),
    ("subcontract", ("subcontract", "paving", "concrete placing", "finishing", "testing", "coring")),
    ("material", ("pipe", "fitting", "concrete", "asphalt", "aggregate", "gravel", "sand", "topsoil")),
)


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


def _procurement_category(description: str) -> str | None:
    normalized = description.casefold()
    return next((category for category, terms in PROCUREMENT_RULES if any(term in normalized for term in terms)), None)


def _initialize_award_controls(project: Project, quote: CustomerQuote, actor_email: str) -> None:
    """Store an idempotent award baseline without treating customer pricing as a cost budget."""
    metadata = dict(project.metadata_json or {})
    baseline = metadata.get("award_pricing_baseline") or {}
    if baseline.get("source_quote_id") == str(quote.id):
        return
    lines = []
    requirements = []
    for index, source in enumerate(quote.line_items_json or [], start=1):
        source_line_id = f"{quote.id}:{index}"
        description = str(source.get("description") or "").strip()
        lines.append({
            "source_line_id": source_line_id,
            "description": description,
            "quantity": source.get("quantity"),
            "unit": source.get("unit"),
            "customer_unit_price": source.get("unit_price"),
            "customer_price_amount": source.get("amount"),
            "cost_code": None,
            "cost_budget_amount": None,
            "status": "needs_cost_allocation",
        })
        category = _procurement_category(description)
        if category:
            requirements.append({
                "requirement_id": source_line_id,
                "source_line_id": source_line_id,
                "category": category,
                "description": description,
                "quantity": source.get("quantity"),
                "unit": source.get("unit"),
                "status": "not_started",
                "vendor_id": None,
                "po_number": None,
                "required_on_site_date": None,
                "approval": None,
            })
    now = datetime.now(UTC).isoformat()
    metadata["award_pricing_baseline"] = {
        "source_quote_id": str(quote.id),
        "source_quote_number": quote.quote_number,
        "source_quote_revision": quote.record_revision,
        "pricing_subtotal": str(quote.subtotal),
        "basis": "accepted_customer_quote_price",
        "cost_budget_status": "needs_cost_allocation",
        "lines": lines,
        "created_by": actor_email,
        "created_at": now,
    }
    metadata["procurement_plan"] = {
        "source_quote_id": str(quote.id),
        "status": "draft",
        "requirements": requirements,
        "created_by": actor_email,
        "created_at": now,
        "automatic_commitment": False,
    }
    project.metadata_json = metadata


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


def _find_estimate_quote(
    db: Session,
    *,
    workspace_id: UUID,
    project_id: UUID,
    estimate_hash: str,
) -> CustomerQuote | None:
    workspace_quote = db.scalar(
        select(CustomerQuote).where(
            CustomerQuote.source_estimate_workspace_id == workspace_id,
        )
    )
    if workspace_quote:
        if workspace_quote.source_estimate_hash != estimate_hash:
            raise AppError(
                "The saved estimate changed after its quote draft was created. Save a new estimate workspace before creating another quote.",
                status_code=409,
            )
        return workspace_quote
    return db.scalar(
        select(CustomerQuote).where(
            CustomerQuote.project_id == project_id,
            CustomerQuote.source_estimate_hash == estimate_hash,
        )
    )


def _estimate_quote_source(bid: Bid) -> tuple[EstimateSummary, str, dict]:
    bid_json = bid.bid_json or {}
    estimate_json = bid_json.get("estimate")
    summary_json = bid_json.get("summary")
    if not isinstance(estimate_json, dict) or not isinstance(summary_json, dict):
        raise AppError(
            "Calculate and save the estimate before creating a customer quote draft.",
            status_code=409,
        )
    try:
        summary = EstimateSummary.model_validate(summary_json)
    except ValidationError as error:
        raise AppError(
            "The saved estimate summary is invalid. Recalculate and save it before creating a quote.",
            status_code=409,
        ) from error
    if summary.final_price <= 0:
        raise AppError(
            "The saved estimate final price must be greater than zero before creating a quote.",
            status_code=409,
        )

    canonical_source = {"estimate": estimate_json, "summary": summary_json}
    estimate_hash = hashlib.sha256(
        json.dumps(
            canonical_source,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    snapshot = {
        "workspace_id": str(bid.id),
        "project_id": str(bid.project_id),
        "workspace_status": bid.status,
        "workspace_created_at": bid.created_at.isoformat(),
        "bid_json": bid_json,
    }
    return summary, estimate_hash, snapshot


def _read(quote: CustomerQuote, project: Project) -> CustomerQuoteRead:
    return CustomerQuoteRead(
        id=quote.id,
        project_id=quote.project_id,
        source_estimate_workspace_id=quote.source_estimate_workspace_id,
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
        issue_status=quote.issue_status,
        approved_revision=quote.approved_revision,
        approved_at=quote.approved_at,
        approved_by=quote.approved_by,
        issued_at=quote.issued_at,
        issued_by=quote.issued_by,
        issuance_method=quote.issuance_method,
        issuance_reference=quote.issuance_reference,
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
    *,
    source_estimate_workspace_id: UUID | None = None,
    source_estimate_hash: str | None = None,
    source_estimate_snapshot: dict | None = None,
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
                source_estimate_workspace_id=source_estimate_workspace_id,
                source_estimate_hash=source_estimate_hash,
                source_estimate_snapshot_json=source_estimate_snapshot,
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
            if source_estimate_workspace_id and source_estimate_hash and payload.project_id:
                existing = _find_estimate_quote(
                    db,
                    workspace_id=source_estimate_workspace_id,
                    project_id=payload.project_id,
                    estimate_hash=source_estimate_hash,
                )
                if existing:
                    return _read(existing, _load_project(db, existing.project_id))
            continue
    raise AppError("Unable to allocate a unique quote number. Try again.", status_code=409)


def create_customer_quote_from_estimate(
    db: Session,
    workspace_id: UUID,
    actor_email: str,
) -> CustomerQuoteRead:
    workspace = db.get(Bid, workspace_id)
    if workspace is None:
        raise AppError("Estimate workspace not found.", status_code=404)
    project = _load_project(db, workspace.project_id)
    if project.status == ProjectStatus.archived.value:
        raise AppError("Archived projects cannot receive quotes.", status_code=409)
    customer_name = (project.client_owner or "").strip()
    if not customer_name:
        raise AppError(
            "Add the customer name to the project before creating a quote draft.",
            status_code=409,
        )

    summary, estimate_hash, snapshot = _estimate_quote_source(workspace)
    existing = _find_estimate_quote(
        db,
        workspace_id=workspace.id,
        project_id=workspace.project_id,
        estimate_hash=estimate_hash,
    )
    if existing:
        return _read(existing, project)

    description = summary.project_name.strip() or project.name
    scope_items = [item.description.strip() for item in summary.line_items if item.description.strip()]
    scope_summary = description
    if scope_items:
        scope_summary = f"{description} — {'; '.join(scope_items)}"
    scope_summary = scope_summary[:10_000].rstrip()
    payload = CustomerQuoteCreate(
        project_id=project.id,
        project_name=project.name,
        customer_name=customer_name,
        site_address=project.project_address,
        scope_summary=scope_summary,
        line_items=[
            CustomerQuoteLineItem(
                description=description,
                quantity=Decimal("1"),
                unit="LS",
                unit_price=Decimal(str(summary.final_price)),
            )
        ],
        assumptions=summary.assumptions,
        exclusions=summary.exclusions,
        gst_rate=Decimal("5.00"),
        quote_date=date.today(),
        notes="Draft generated from a saved estimate. Review customer details, scope, and terms before issue.",
    )
    return create_customer_quote(
        db,
        payload,
        actor_email,
        source_estimate_workspace_id=workspace.id,
        source_estimate_hash=estimate_hash,
        source_estimate_snapshot=snapshot,
    )


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
    if quote.issue_status in {
        CustomerQuoteIssueStatus.approved_for_issue.value,
        CustomerQuoteIssueStatus.issued.value,
    }:
        raise AppError("Approved or issued quote revisions are immutable. Start a new controlled revision.", status_code=409)
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
    quote.issue_status = CustomerQuoteIssueStatus.draft.value

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
    if payload.status == CustomerQuoteStatus.sent:
        raise AppError("Approve the quote revision and record issuance through the controlled issue action.", status_code=409)
    now = datetime.now(UTC)
    quote.status = payload.status.value
    quote.record_revision += 1
    if payload.note:
        quote.notes = payload.note.strip()
    quote.closed_at = now
    db.commit()
    project = _load_project(db, quote.project_id)
    db.refresh(quote)
    return _read(quote, project)


def update_customer_quote_issue_status(
    db: Session,
    quote_id: UUID,
    payload: CustomerQuoteIssueUpdate,
    actor_email: str,
) -> CustomerQuoteRead:
    quote = _load_quote(db, quote_id, for_update=True)
    project = _load_project(db, quote.project_id)
    if quote.record_revision != payload.expected_revision:
        raise AppError("This quote changed in another session. Reload before continuing.", status_code=409)
    if quote.status in {
        CustomerQuoteStatus.accepted.value,
        CustomerQuoteStatus.declined.value,
        CustomerQuoteStatus.expired.value,
    }:
        raise AppError("Closed quotes cannot move through issue review.", status_code=409)

    now = datetime.now(UTC)
    target = payload.status
    if target == CustomerQuoteIssueStatus.ready_for_review:
        if quote.issue_status != CustomerQuoteIssueStatus.draft.value:
            raise AppError("Only draft revisions can be submitted for review.", status_code=409)
        quote.issue_status = target.value
    elif target == CustomerQuoteIssueStatus.approved_for_issue:
        if quote.issue_status != CustomerQuoteIssueStatus.ready_for_review.value:
            raise AppError("The revision must be ready for review before approval.", status_code=409)
        quote.issue_status = target.value
        quote.approved_revision = quote.record_revision
        quote.approved_at = now
        quote.approved_by = actor_email
        snapshot = _read(quote, project).model_dump(mode="json")
        snapshot["issue_status"] = CustomerQuoteIssueStatus.approved_for_issue.value
        quote.approved_snapshot_json = snapshot
        existing = next(
            (
                document
                for document in db.scalars(
                    select(Document).where(
                        Document.project_id == quote.project_id,
                        Document.category == "quote",
                    )
                ).all()
                if (document.metadata_json or {}).get("customer_quote_id") == str(quote.id)
                and (document.metadata_json or {}).get("quote_revision") == quote.record_revision
            ),
            None,
        )
        if existing is None:
            db.add(Document(
                title=f"{quote.quote_number} revision {quote.record_revision}",
                category="quote",
                status="current",
                project_id=quote.project_id,
                description="Approved customer quote PDF generated from the controlled IHOS revision.",
                revision=str(quote.record_revision),
                issue_date=quote.quote_date,
                metadata_json={
                    "source": "customer_quote",
                    "customer_quote_id": str(quote.id),
                    "quote_revision": quote.record_revision,
                    "generated_pdf_path": f"/api/v1/customer-quotes/{quote.id}/pdf",
                },
            ))
    elif target == CustomerQuoteIssueStatus.issued:
        if quote.issue_status != CustomerQuoteIssueStatus.approved_for_issue.value:
            raise AppError("Only an approved revision can be recorded as issued.", status_code=409)
        if not payload.issuance_method or not payload.issuance_reference:
            raise AppError("Issuance method and reference are required.", status_code=422)
        quote.issue_status = target.value
        quote.issued_at = now
        quote.issued_by = actor_email
        quote.issuance_method = payload.issuance_method.strip()
        quote.issuance_reference = payload.issuance_reference.strip()
        quote.status = CustomerQuoteStatus.sent.value
        quote.sent_at = now
    else:
        raise AppError("Unsupported quote issue transition.", status_code=422)

    quote.record_revision += 1
    db.commit()
    db.refresh(quote)
    return _read(quote, project)


def get_customer_quote_pdf_snapshot(db: Session, quote_id: UUID) -> CustomerQuoteRead:
    quote = _load_quote(db, quote_id)
    if quote.approved_snapshot_json:
        return CustomerQuoteRead.model_validate(quote.approved_snapshot_json)
    return _read(quote, _load_project(db, quote.project_id))


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
            _initialize_award_controls(project, quote, actor_email)
            db.commit()
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
            _initialize_award_controls(project, quote, actor_email)
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(quote)
        db.refresh(project)
        return _read(quote, project)
    raise AppError("Unable to allocate a unique job number. Try again.", status_code=409)
