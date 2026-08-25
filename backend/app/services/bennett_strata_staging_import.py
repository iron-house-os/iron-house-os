"""Controlled staging intake for issue #314 Bennett Strata estimates."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.project import Project
from app.schemas.estimate import EstimateCreate
from app.services.drive_tender_import import ImportValidationError
from app.services.estimates import calculate_estimate

SOURCE_KEY = "bennett_strata_issue_314"
PROJECT_NUMBER = "STAGE-BENNETT-2026"
TARGET_MARGIN = Decimal("30")
FLOOR_MARGIN = Decimal("20")
GST_RATE = Decimal("5")


def _profit_markup_for_margin(margin_percent: Decimal) -> float:
    fraction = margin_percent / Decimal("100")
    return float((fraction / (Decimal("1") - fraction)) * Decimal("100"))


def _price(cost: Decimal, margin_percent: Decimal) -> Decimal:
    return (cost / (Decimal("1") - margin_percent / Decimal("100"))).quantize(Decimal("0.01"))


def _estimate_definitions() -> tuple[dict[str, object], ...]:
    return (
        {
            "key": "concrete",
            "name": "Bennett Strata - Concrete Pull & Pour",
            "cost": Decimal("26660.93"),
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
                "30% true profit margin is the target pricing scenario; 20% is the lower-margin comparison.",
            ],
            "exclusions": ["Conditions materially beyond the included subgrade/buried-deficiency allowance require change-order review."],
        },
        {
            "key": "asphalt",
            "name": "Bennett Strata - Asphalt Restoration",
            "cost": Decimal("12300.00"),
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
                "30% true profit margin is the target pricing scenario; 20% is the lower-margin comparison.",
            ],
            "exclusions": ["Conditions materially beyond the included subgrade/buried-deficiency allowance require change-order review."],
        },
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

    project = db.scalar(select(Project).where(Project.project_number == PROJECT_NUMBER))
    if project is None:
        same_name = list(db.scalars(select(Project).where(Project.name == "Bennett Strata - Bennett Road")).all())
        if len(same_name) > 1:
            raise ImportValidationError("Multiple Bennett Strata projects already exist.")
        project = same_name[0] if same_name else None
    project_existed = project is not None

    records: list[dict[str, object]] = []
    if apply and project is None:
        project = Project(name="Bennett Strata - Bennett Road", project_number=PROJECT_NUMBER)
        db.add(project)
        db.flush()

    if apply and project is not None:
        project.name = "Bennett Strata - Bennett Road"
        project.client_owner = "Bennett Strata"
        project.municipality_name = "Richmond, BC"
        project.project_address = "Bennett Road, Richmond, BC"
        project.status = "opportunity"
        project.description = "Separate concrete pull-and-pour and asphalt restoration estimates."
        metadata = dict(project.metadata_json or {})
        metadata[SOURCE_KEY] = {
            "issue": 314,
            "site_photo_count": 19,
            "workflow": ["estimate", "review", "customer_quote", "award", "project_job_number", "budget_cost_codes", "procurement_rentals", "safety", "field_production_photos", "actual_cost", "invoice_closeout"],
            "job_number_policy": "Create once on award/authorization; not before.",
            "audit_actor": actor,
            "imported_at": timestamp,
        }
        project.metadata_json = metadata
        db.flush()

    existing_bids = list(db.scalars(select(Bid).where(Bid.project_id == project.id)).all()) if project is not None else []

    for definition in _estimate_definitions():
        cost = definition["cost"]
        target_sell = _price(cost, TARGET_MARGIN)
        floor_sell = _price(cost, FLOOR_MARGIN)
        target_total = (target_sell * (Decimal("1") + GST_RATE / Decimal("100"))).quantize(Decimal("0.01"))
        floor_total = (floor_sell * (Decimal("1") + GST_RATE / Decimal("100"))).quantize(Decimal("0.01"))
        payload = EstimateCreate(
            project_name=definition["name"],
            owner="Bennett Strata",
            line_items=definition["line_items"],
            risks=definition["risks"],
            markup={"profit_percent": _profit_markup_for_margin(TARGET_MARGIN)},
            assumptions=definition["assumptions"],
            exclusions=definition["exclusions"],
            target_margin_percent=float(TARGET_MARGIN),
            planned_field_shifts=2,
        )
        summary = calculate_estimate(payload)
        matching = [
            bid for bid in existing_bids
            if (bid.bid_json or {}).get("source") == SOURCE_KEY
            and (bid.bid_json or {}).get("estimate_key") == definition["key"]
        ]
        if len(matching) > 1:
            raise ImportValidationError(f"Multiple Bennett {definition['key']} workspaces exist.")
        bid = matching[0] if matching else None
        action = "update" if bid else "create"
        record = {
            "estimate_key": definition["key"],
            "project": definition["name"],
            "action": action,
            "cost_basis_cad": float(cost),
            "floor_20_percent_before_gst_cad": float(floor_sell),
            "floor_20_percent_total_cad": float(floor_total),
            "target_30_percent_before_gst_cad": float(target_sell),
            "target_30_percent_total_cad": float(target_total),
            "calculated_target_cad": summary.final_price,
        }
        if apply:
            if project is None:
                raise ImportValidationError("Bennett project was not created.")
            if bid is None:
                bid = Bid(project_id=project.id)
                db.add(bid)
                existing_bids.append(bid)
            bid.status = "draft"
            bid.total_amount = target_sell
            bid.summary = f"{definition['name']} — 30% true margin target; 20% floor comparison retained in pricing scenarios."
            bid.bid_json = {
                "source": SOURCE_KEY,
                "estimate_key": definition["key"],
                "estimate": payload.model_dump(mode="json"),
                "summary": summary.model_dump(mode="json"),
                "pricing_scenarios": {
                    "20_percent_margin": {"before_gst": float(floor_sell), "gst": float(floor_total - floor_sell), "total": float(floor_total)},
                    "30_percent_margin": {"before_gst": float(target_sell), "gst": float(target_total - target_sell), "total": float(target_total)},
                },
                "site_photo_count": 19,
                "audit_actor": actor,
                "imported_at": timestamp,
            }
            db.flush()
            record["workspace_id"] = str(bid.id)
        records.append(record)

    return {
        "status": "applied" if apply else "dry_run",
        "source": SOURCE_KEY,
        "staging_only": True,
        "project_action": "update" if project_existed else "create",
        "project_id": str(project.id) if apply and project is not None else None,
        "records": records,
        "actor": actor,
        "imported_at": timestamp,
    }
