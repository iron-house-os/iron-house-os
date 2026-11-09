from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.bid import Bid
from app.models.project import Project
from app.schemas.estimate import EstimateCreate, EstimateItemType, EstimateLineItem
from app.schemas.quote_integration import (
    QuoteEstimateHandoffRequest,
    QuoteEstimateHandoffResponse,
    QuoteEstimateSelectionRequest,
    SupplierQuoteCreate,
    SupplierQuoteRead,
)
from app.services import estimate_workspace, estimates, quotes
from app.services.quote_selection import select_quotes_for_estimate

HANDOFF_SOURCE = "quote_estimate_handoff"


def handoff_saved_quotes(
    db: Session,
    payload: QuoteEstimateHandoffRequest,
) -> QuoteEstimateHandoffResponse:
    project = db.get(Project, payload.project_id)
    if project is None:
        raise AppError("Project not found", status_code=404)

    saved_quotes = quotes.list_quotes(db, payload.project_id)
    selection = select_quotes_for_estimate(
        QuoteEstimateSelectionRequest(
            quotes=[_quote_input(quote) for quote in saved_quotes],
        )
    )
    if not selection.ready_for_estimate:
        details = "; ".join(selection.blockers) or "Supplier quote selection is incomplete."
        raise AppError(
            f"Supplier quote handoff is blocked: {details}",
            status_code=409,
        )

    quote_fingerprint = _quote_fingerprint(saved_quotes)
    source_quote_ids = sorted((quote.id for quote in saved_quotes), key=str)
    latest = _latest_parseable_draft(db, payload.project_id)
    if latest is not None and _is_matching_handoff(latest, quote_fingerprint):
        metadata = latest.bid_json.get("quote_handoff", {})
        return QuoteEstimateHandoffResponse(
            project_id=payload.project_id,
            workspace=estimate_workspace.get_workspace(db, latest.id),
            created=False,
            applied_line_count=int(metadata.get("applied_line_count", 0)),
            source_quote_ids=source_quote_ids,
        )

    source_bid, base_estimate = _source_estimate(latest, project)
    merged_estimate = _merge_selected_quotes(base_estimate, selection.line_items)
    summary = estimates.calculate_estimate(merged_estimate)
    source_estimate_sha256 = _json_sha256(base_estimate.model_dump(mode="json"))
    bid = Bid(
        project_id=payload.project_id,
        tender_id=source_bid.tender_id if source_bid is not None else None,
        status="draft",
        total_amount=summary.final_price,
        summary=(
            f"Draft estimate with {len(merged_estimate.line_items)} line items; "
            f"{len(selection.line_items)} supplier-priced line(s) applied."
        ),
        bid_json={
            "estimate": merged_estimate.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json"),
            "source": HANDOFF_SOURCE,
            "quote_handoff": {
                "project_id": str(payload.project_id),
                "source_workspace_id": str(source_bid.id) if source_bid is not None else None,
                "source_estimate_sha256": source_estimate_sha256,
                "quote_fingerprint": quote_fingerprint,
                "source_quote_ids": [str(quote_id) for quote_id in source_quote_ids],
                "applied_line_count": len(selection.line_items),
            },
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return QuoteEstimateHandoffResponse(
        project_id=payload.project_id,
        workspace=estimate_workspace.get_workspace(db, bid.id),
        created=True,
        applied_line_count=len(selection.line_items),
        source_quote_ids=source_quote_ids,
    )


def _quote_input(quote: SupplierQuoteRead) -> SupplierQuoteCreate:
    return SupplierQuoteCreate.model_validate(
        quote.model_dump(
            exclude={"id", "project_id", "created_at", "updated_at"},
        )
    )


def _quote_fingerprint(saved_quotes: list[SupplierQuoteRead]) -> str:
    payload = [
        quote.model_dump(mode="json", exclude={"created_at", "updated_at"})
        for quote in sorted(saved_quotes, key=lambda item: str(item.id))
    ]
    return _json_sha256(payload)


def _json_sha256(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _latest_parseable_draft(db: Session, project_id: UUID) -> Bid | None:
    candidates = db.scalars(
        select(Bid)
        .where(Bid.project_id == project_id, Bid.status == "draft")
        .order_by(Bid.created_at.desc(), Bid.id.desc())
    ).all()
    for candidate in candidates:
        if _read_estimate(candidate) is not None:
            return candidate
    return None


def _source_estimate(latest: Bid | None, project: Project) -> tuple[Bid | None, EstimateCreate]:
    if latest is not None:
        estimate = _read_estimate(latest)
        if estimate is not None:
            return latest, estimate
    return (
        None,
        EstimateCreate(
            project_name=project.name,
            project_code=project.project_number or project.tender_number,
        ),
    )


def _read_estimate(bid: Bid) -> EstimateCreate | None:
    container = bid.bid_json or {}
    candidate = container.get("estimate", container)
    if isinstance(candidate, dict) and isinstance(candidate.get("estimate"), dict):
        candidate = candidate["estimate"]
    try:
        return EstimateCreate.model_validate(candidate)
    except (TypeError, ValidationError):
        return None


def _is_matching_handoff(bid: Bid, quote_fingerprint: str) -> bool:
    payload = bid.bid_json or {}
    metadata = payload.get("quote_handoff")
    return (
        payload.get("source") == HANDOFF_SOURCE
        and isinstance(metadata, dict)
        and metadata.get("quote_fingerprint") == quote_fingerprint
    )


def _merge_selected_quotes(
    estimate: EstimateCreate,
    selected_lines: list[EstimateLineItem],
) -> EstimateCreate:
    merged_lines = [item.model_copy(deep=True) for item in estimate.line_items]
    positions: dict[str, list[int]] = defaultdict(list)
    for index, line in enumerate(merged_lines):
        code = _normalise_code(line.code)
        if code:
            positions[code].append(index)

    for selected in selected_lines:
        code = _normalise_code(selected.code)
        matches = positions.get(code, []) if code else []
        if len(matches) > 1:
            raise AppError(
                f"Estimate line item code {selected.code} is duplicated; "
                "resolve the ambiguity before applying supplier quotes.",
                status_code=409,
            )
        if not matches:
            merged_lines.append(selected.model_copy(deep=True))
            if code:
                positions[code].append(len(merged_lines) - 1)
            continue
        index = matches[0]
        merged_lines[index] = _merge_line(merged_lines[index], selected)

    return estimate.model_copy(update={"line_items": merged_lines}, deep=True)


def _merge_line(existing: EstimateLineItem, selected: EstimateLineItem) -> EstimateLineItem:
    updates: dict[str, object] = {
        "item_type": selected.item_type,
        "vendor_quotes": selected.vendor_quotes,
        "direct_unit_cost": None,
        "notes": existing.notes or selected.notes,
    }
    if selected.item_type == EstimateItemType.material:
        updates["materials"] = []
    else:
        updates["subcontract"] = None
    return existing.model_copy(update=updates, deep=True)


def _normalise_code(code: str | None) -> str:
    return (code or "").strip().casefold()
