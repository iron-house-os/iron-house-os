"""Controlled staging intake for the issue #314 Bennett Strata estimates."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.project import Project
from app.schemas.estimate import EstimateCreate
from app.services.drive_tender_import import ImportValidationError
from app.services.estimates import calculate_estimate

SOURCE_KEY = "bennett_strata_issue_314"
SOURCE_REVISION = "2026-08-27-final"
PROJECT_NAME = "Bennett Strata - Bennett Road"
LEGACY_PROJECT_NUMBER = "STAGE-BENNETT-2026"
GST_RATE = Decimal("5")
FLOOR_MARGIN = Decimal("20")
MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _before_gst(total: Decimal) -> Decimal:
    return _money(total / (Decimal("1") + GST_RATE / Decimal("100")))


def _price(cost: Decimal, margin_percent: Decimal) -> Decimal:
    return _money(cost / (Decimal("1") - margin_percent / Decimal("100")))


def _profit_markup_for_sell(cost: Decimal, sell: Decimal) -> float:
    return float((sell / cost - Decimal("1")) * Decimal("100"))


def _option(option_id: str, description: str, total: str) -> dict[str, object]:
    total_amount = Decimal(total)
    subtotal = _before_gst(total_amount)
    return {
        "option_id": option_id,
        "description": description,
        "subtotal": float(subtotal),
        "gst": float(total_amount - subtotal),
        "total": float(total_amount),
    }


def _estimate_definitions() -> tuple[dict[str, Any], ...]:
    return (
        {
            "key": "concrete",
            "name": "Bennett Strata - Concrete Pull & Pour",
            "cost": Decimal("26660.93"),
            "approved_total": Decimal("38080.00"),
            "line_items": [
                {"code": "CON-001", "description": "4 in concrete pull and pour", "quantity": 108.6, "unit": "m2", "direct_unit_cost": 182.88144603841996},
                {"code": "EQP-001", "description": "14 in cutoff saw incl. blade wear and consumables", "quantity": 1, "unit": "day", "direct_unit_cost": 200.00},
                {"code": "EQP-002", "description": "Skid steer with hydraulic hammer for removal, loading and preparation", "quantity": 1, "unit": "day", "direct_unit_cost": 1100.00},
                {"code": "TRK-001", "description": "Tandem allowance for concrete disposal", "quantity": 1, "unit": "LS", "direct_unit_cost": 750.00},
            ],
            "risks": [{"description": "Subgrade / buried deficiencies provisional allowance", "amount": 4750.00, "probability": 1.0, "notes": "Localized excavation/export, imported compactable base, geotextile where required, compaction and related labour/equipment/trucking."}],
            "assumptions": [
                "Concrete thickness is 4 in.",
                "Measured concrete area is 108.60 m2.",
                "Removal and preparation are planned for day 1; placement and finishing for day 2.",
                "Ready-mix concrete will be ordered for delivery.",
                "19 site photos document cracking, settlement, failed interfaces and constrained access.",
            ],
            "exclusions": ["Conditions materially beyond the included subgrade/buried-deficiency allowance require change-order review."],
            "customer_options": None,
        },
        {
            "key": "asphalt",
            "name": "Bennett Strata - Asphalt Restoration",
            "cost": Decimal("12300.00"),
            "approved_total": Decimal("20223.68"),
            "line_items": [
                {"code": "ASP-001", "description": "2 in asphalt restoration including cut, pull, base prep, supply, place and compact", "quantity": 62.0, "unit": "m2", "direct_unit_cost": 120.16129032258064},
                {"code": "EQP-001", "description": "14 in cutoff saw incl. blade wear and consumables", "quantity": 1, "unit": "day", "direct_unit_cost": 200.00},
                {"code": "EQP-002", "description": "Skid steer with hydraulic hammer for asphalt removal, loading and prep", "quantity": 1, "unit": "day", "direct_unit_cost": 1100.00},
                {"code": "EQP-003", "description": "Double-drum asphalt roller incl. delivery/pickup", "quantity": 1, "unit": "day", "direct_unit_cost": 450.00},
                {"code": "TRK-002", "description": "Tandem allowance for asphalt disposal and HMA pickup/delivery", "quantity": 1, "unit": "LS", "direct_unit_cost": 600.00},
            ],
            "risks": [{"description": "Subgrade / buried deficiencies provisional allowance", "amount": 2500.00, "probability": 1.0, "notes": "Localized excavation/export, imported compactable base, geotextile where required, compaction and related labour/equipment/trucking."}],
            "assumptions": [
                "Asphalt thickness is 2 in compacted.",
                "Measured asphalt area is 62.00 m2.",
                "Approximately 8 tonnes HMA will be required.",
                "19 site photos document cracking, settlement, failed interfaces and constrained access.",
            ],
            "exclusions": ["Conditions materially beyond the included subgrade/buried-deficiency allowance require change-order review."],
            "customer_options": {
                "mutually_exclusive": True,
                "selected_option_id": None,
                "draft_selected_options_total": 0.0,
                "items": [
                    _option("option_1", "Remove pavers and prepare and place asphalt", "3990.00"),
                    _option("option_2", "Remove pavers, re-prepare, and install new 2 ft x 2 ft pavers", "8561.54"),
                    _option("option_3", "Remove pavers and prepare, place, and finish concrete", "8960.00"),
                ],
            },
        },
    )


def _find_project(db: Session) -> Project | None:
    projects = list(db.scalars(select(Project)).all())
    candidates: dict[object, Project] = {}
    for project in projects:
        metadata = project.metadata_json or {}
        if SOURCE_KEY in metadata or project.project_number == LEGACY_PROJECT_NUMBER or project.name == PROJECT_NAME:
            candidates[project.id] = project
    if len(candidates) > 1:
        raise ImportValidationError("Multiple Bennett Strata staging projects already exist.")
    return next(iter(candidates.values()), None)


def _project_number_action(project: Project | None) -> str:
    if project is None or not project.project_number:
        return "none"
    if project.project_number != LEGACY_PROJECT_NUMBER:
        raise ImportValidationError(
            "The Bennett staging project has an unexpected non-empty project number. Manual review is required."
        )
    if project.status != "opportunity":
        raise ImportValidationError(
            "The legacy Bennett staging project number cannot be cleared after the project leaves opportunity status."
        )
    return "clear_legacy_marker"


def _source_payload(
    definition: dict[str, Any],
    *,
    actor: str,
    imported_at: str,
) -> tuple[dict[str, Any], Decimal, Decimal, Decimal, Decimal]:
    cost = definition["cost"]
    approved_total = definition["approved_total"]
    approved_subtotal = _before_gst(approved_total)
    approved_gst = approved_total - approved_subtotal
    floor_sell = _price(cost, FLOOR_MARGIN)
    payload = EstimateCreate(
        project_name=definition["name"],
        owner="Bennett Strata",
        line_items=definition["line_items"],
        risks=definition["risks"],
        markup={"profit_percent": _profit_markup_for_sell(cost, approved_subtotal)},
        assumptions=definition["assumptions"],
        exclusions=definition["exclusions"],
        target_margin_percent=float((approved_subtotal - cost) / approved_subtotal * Decimal("100")),
        planned_field_shifts=2,
    )
    summary = calculate_estimate(payload)
    if Decimal(str(summary.final_price)) != approved_subtotal:
        raise ImportValidationError(
            f"Calculated {definition['key']} subtotal does not match the approved source revision."
        )
    bid_json = {
        "source": SOURCE_KEY,
        "source_revision": SOURCE_REVISION,
        "estimate_key": definition["key"],
        "estimate": payload.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
        "approved_customer_quote": {
            "currency": "CAD",
            "subtotal": float(approved_subtotal),
            "gst": float(approved_gst),
            "total": float(approved_total),
        },
        "pricing_scenarios": {
            "20_percent_margin_floor": {
                "before_gst": float(floor_sell),
                "gst": float(_money(floor_sell * GST_RATE / Decimal("100"))),
                "total": float(_money(floor_sell * (Decimal("1") + GST_RATE / Decimal("100")))),
            },
            "approved_final": {
                "before_gst": float(approved_subtotal),
                "gst": float(approved_gst),
                "total": float(approved_total),
            },
        },
        "customer_options": definition["customer_options"],
        "site_photo_count": 19,
        "audit_actor": actor,
        "imported_at": imported_at,
    }
    return bid_json, cost, floor_sell, approved_subtotal, approved_total


def _same_immutable_source(existing: dict, expected: dict) -> bool:
    excluded = {"audit_actor", "imported_at"}
    return (
        {key: value for key, value in existing.items() if key not in excluded}
        == {key: value for key, value in expected.items() if key not in excluded}
    )


def import_bennett_strata_estimates(
    db: Session,
    *,
    actor: str,
    apply: bool = False,
    imported_at: datetime | None = None,
) -> dict[str, object]:
    actor = actor.strip()
    if not actor:
        raise ImportValidationError("An audit actor is required.")
    timestamp = (imported_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()

    project = _find_project(db)
    project_existed = project is not None
    project_number_action = _project_number_action(project)
    if project is not None and project.status != "opportunity":
        raise ImportValidationError(
            "The Bennett staging source must remain an opportunity for the draft quote pilot."
        )

    records: list[dict[str, object]] = []
    if apply and project is None:
        project = Project(name=PROJECT_NAME, status="opportunity")
        db.add(project)
        db.flush()

    if apply and project is not None:
        if project_number_action == "clear_legacy_marker":
            project.project_number = None
        project.name = PROJECT_NAME
        project.client_owner = "Bennett Strata"
        project.municipality_name = "Richmond, BC"
        project.project_address = "Bennett Road, Richmond, BC"
        project.status = "opportunity"
        project.description = "Separate concrete pull-and-pour and asphalt restoration estimates."
        metadata = dict(project.metadata_json or {})
        source_metadata = dict(metadata.get(SOURCE_KEY) or {})
        revisions = dict(source_metadata.get("revisions") or {})
        revisions.setdefault(
            SOURCE_REVISION,
            {
                "issue": 314,
                "site_photo_count": 19,
                "audit_actor": actor,
                "imported_at": timestamp,
                "status": "draft_source",
            },
        )
        source_metadata.update(
            {
                "issue": 314,
                "latest_source_revision": SOURCE_REVISION,
                "site_photo_count": 19,
                "workflow": [
                    "estimate",
                    "review",
                    "customer_quote",
                    "award",
                    "project_job_number",
                    "budget_cost_codes",
                    "procurement_rentals",
                    "safety",
                    "field_production_photos",
                    "actual_cost",
                    "invoice_closeout",
                ],
                "job_number_policy": "Create once on explicit award/authorization; never use a staging source marker.",
                "revisions": revisions,
            }
        )
        metadata[SOURCE_KEY] = source_metadata
        project.metadata_json = metadata
        db.flush()

    existing_bids = (
        list(db.scalars(select(Bid).where(Bid.project_id == project.id)).all())
        if project is not None
        else []
    )

    for definition in _estimate_definitions():
        expected_bid_json, cost, floor_sell, approved_subtotal, approved_total = _source_payload(
            definition,
            actor=actor,
            imported_at=timestamp,
        )
        matching = [
            bid
            for bid in existing_bids
            if (bid.bid_json or {}).get("source") == SOURCE_KEY
            and (bid.bid_json or {}).get("source_revision") == SOURCE_REVISION
            and (bid.bid_json or {}).get("estimate_key") == definition["key"]
        ]
        if len(matching) > 1:
            raise ImportValidationError(
                f"Multiple Bennett {definition['key']} workspaces exist for {SOURCE_REVISION}."
            )
        bid = matching[0] if matching else None
        if bid is not None and not _same_immutable_source(bid.bid_json or {}, expected_bid_json):
            raise ImportValidationError(
                f"The Bennett {definition['key']} {SOURCE_REVISION} workspace differs from the approved immutable source."
            )
        action = "reuse" if bid else "create"
        record: dict[str, object] = {
            "estimate_key": definition["key"],
            "source_revision": SOURCE_REVISION,
            "project": definition["name"],
            "action": action,
            "cost_basis_cad": float(cost),
            "floor_20_percent_before_gst_cad": float(floor_sell),
            "approved_before_gst_cad": float(approved_subtotal),
            "approved_gst_cad": float(approved_total - approved_subtotal),
            "approved_total_cad": float(approved_total),
            "calculated_approved_cad": expected_bid_json["summary"]["final_price"],
        }
        if apply:
            if project is None:
                raise ImportValidationError("Bennett project was not created.")
            if bid is None:
                bid = Bid(
                    project_id=project.id,
                    status="draft",
                    total_amount=approved_subtotal,
                    summary=(
                        f"{definition['name']} — authoritative {SOURCE_REVISION} draft; "
                        f"customer total {approved_total:.2f} including GST."
                    ),
                    bid_json=expected_bid_json,
                )
                db.add(bid)
                db.flush()
                existing_bids.append(bid)
            record["workspace_id"] = str(bid.id)
        records.append(record)

    return {
        "status": "applied" if apply else "dry_run",
        "source": SOURCE_KEY,
        "source_revision": SOURCE_REVISION,
        "staging_only": True,
        "project_action": "reuse" if project_existed else "create",
        "project_number_action": project_number_action,
        "project_id": str(project.id) if apply and project is not None else None,
        "records": records,
        "actor": actor,
        "imported_at": timestamp,
    }
