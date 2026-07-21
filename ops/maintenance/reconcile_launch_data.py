#!/usr/bin/env python3
"""Idempotently load the first real Iron House OS production records.

This maintenance action:
- reconciles the 100-row supplier master without duplicating suppliers;
- preserves manually-added supplier contacts while removing known bounced inboxes;
- archives release-smoke projects (it does not delete them);
- creates or updates the Downes Road draft-only project; and
- stores the approved $89,870.51 estimate, rounded to a $90,000 bid before GST.

It never sends RFQs or submits a bid.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


MASTER_PATH = Path(__file__).with_name("supplier_master_100.json")
SOURCE_WORKBOOK = "Iron_House_RFQ_Supplier_Master_100_Grouped.xlsx"
DOWNES_PROJECT_NUMBER = "DOWNES-RD-2026-DRAFT"
DOWNES_ESTIMATE_SOURCE = "downes-road-draft-2026-07-20-v2"
MONEY = Decimal("0.01")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PREFERRED_SUPPLIERS = {
    "emco waterworks - abbotsford",
    "emco waterworks - langley",
    "amrize / lafarge - surrey",
    "lafarge canada / amrize - aggregates bc",
    "superior paving",
    "advanced testing",
    "jws concrete",
    "performance coring",
}

CONTACT_OVERRIDES = {
    "EMCO Waterworks - Abbotsford": {
        "emails": ["MConnolly@emcoltd.com"],
        "bounced_emails": ["abbotsford@emcoltd.com"],
        "status": "active",
        "note": "Abbotsford branch inbox bounced; use MConnolly@emcoltd.com.",
    },
    "Performance Coring": {
        "emails": [],
        "bounced_emails": ["info@performancecoring.ca"],
        "status": "bounced",
        "note": "Known preferred coring supplier; email bounced and needs a replacement contact.",
    },
    "BA Blacktop": {
        "emails": [
            "serafino.vignone@bablacktop.com",
            "charles.monteiro@bablacktop.com",
        ],
        "bounced_emails": [],
        "status": "active",
        "note": "Future bid contacts confirmed; declined T2026-017 only because of backlog.",
    },
    "Herc Rentals - Surrey": {
        "emails": ["customercare@hercrentals.com"],
        "bounced_emails": [],
        "status": "active",
        "note": "Primary RFQ intake updated July 6, 2026.",
    },
    "Herc Rentals - Port Coquitlam": {
        "emails": ["customercare@hercrentals.com"],
        "bounced_emails": [],
        "status": "active",
        "note": "Primary RFQ intake updated July 6, 2026.",
    },
    "Mainland Sand & Gravel": {
        "emails": [],
        "bounced_emails": ["info@mainlandcm.com"],
        "status": "bounced",
        "note": "Generic inbox was blocked; do not use until a replacement aggregate contact is confirmed.",
    },
    "Winvan Paving": {
        "emails": ["winvanestimating@mainlandcm.com"],
        "bounced_emails": [],
        "status": "active",
        "note": "Estimating inbox replied and requested project details/mobilization counts.",
    },
}


def _money(value: Decimal | str | float) -> float:
    return float(Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP))


def _split_emails(value: object) -> list[str]:
    if value is None:
        return []
    candidates = re.split(r"[;,\s]+", str(value).strip())
    return [candidate for candidate in candidates if candidate and EMAIL_RE.match(candidate)]


def _status_from_row(row: dict) -> str:
    value = str(row.get("Status") or "").strip().lower()
    if "needs" in value or "web sourced" in value:
        return "needs_verification"
    return "active"


def _load_master() -> list[dict]:
    rows = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    if len(rows) != 100:
        raise RuntimeError(f"Expected 100 supplier rows; found {len(rows)}")
    names = [str(row.get("Supplier") or "").strip() for row in rows]
    if not all(names) or len({name.casefold() for name in names}) != len(names):
        raise RuntimeError("Supplier master contains blank or duplicate names")
    return rows


def _supplier_record(row: dict) -> dict:
    name = str(row["Supplier"]).strip()
    override = CONTACT_OVERRIDES.get(name, {})
    emails = list(override.get("emails", _split_emails(row.get("RFQ Email"))))
    bounced = list(override.get("bounced_emails", []))
    preferred = name.casefold() in PREFERRED_SUPPLIERS
    status = str(override.get("status", _status_from_row(row)))
    if preferred and status == "needs_verification" and emails:
        status = "active"
    notes = [str(row.get("Notes") or "").strip(), str(override.get("note") or "").strip()]
    metadata = {
        "status": status,
        "preferred": preferred,
        "scope_products": row.get("Scope / Products"),
        "address": row.get("Address / Location"),
        "source": SOURCE_WORKBOOK,
        "source_url": row.get("Source URL"),
        "priority": row.get("Priority"),
        "source_status": row.get("Status"),
        "bounced_emails": bounced,
        "last_reconciled_at": datetime.now(UTC).isoformat(),
    }
    return {
        "name": name,
        "category": row.get("Category"),
        "service_area": row.get("Service Area"),
        "website": row.get("Website"),
        "phone": row.get("Phone"),
        "notes": " ".join(note for note in notes if note),
        "metadata": metadata,
        "emails": emails,
        "bounced_emails": bounced,
    }


def _downes_payload() -> dict:
    final_price = Decimal("89870.51")
    target_margin = Decimal("0.125")
    contingency_rate = Decimal("0.03")
    overhead_rate = Decimal("0.10")
    direct_cost = final_price * (Decimal("1") - target_margin) / (
        (Decimal("1") + contingency_rate) * (Decimal("1") + overhead_rate)
    )
    contingency = direct_cost * contingency_rate
    overhead = (direct_cost + contingency) * overhead_rate
    profit = final_price - direct_cost - contingency - overhead
    scope_basis = direct_cost - Decimal("4000") - Decimal("2690")
    profit_markup_equivalent = target_margin / (Decimal("1") - target_margin) * Decimal("100")

    line_items = [
        {
            "code": "DR-001",
            "description": "Drainage reinstatement - current direct-cost basis",
            "item_type": "self_perform",
            "quantity": 1,
            "unit": "LS",
            "direct_unit_cost": _money(scope_basis),
            "notes": "Includes current known work excluding the separately shown headwall and pickup allocation.",
        },
        {
            "code": "DR-002",
            "description": "Headwall allowance with IHCC installation",
            "item_type": "material",
            "quantity": 1,
            "unit": "LS",
            "direct_unit_cost": 4000.0,
            "notes": "Current instructed allowance.",
        },
        {
            "code": "DR-003",
            "description": "Two-pickup cost recovery - five-day allocation",
            "item_type": "indirect",
            "quantity": 5,
            "unit": "day",
            "direct_unit_cost": 538.0,
            "notes": "$10,760 monthly fleet cost; $538/day recovery; five days allocated.",
        },
    ]
    estimate = {
        "project_name": "Downes Road Drainage Reinstatement",
        "project_code": DOWNES_PROJECT_NUMBER,
        "owner": None,
        "estimator": "Iron House Civil Constructors",
        "line_items": line_items,
        "indirects": [],
        "risks": [],
        "markup": {
            "contingency_percent": 3.0,
            "overhead_percent": 10.0,
            "profit_percent": float(profit_markup_equivalent),
            "bonding_percent": 0.0,
            "insurance_percent": 0.0,
        },
        "assumptions": [
            "Draft estimate only; do not send RFQs and do not submit a bid.",
            "Headwall allowance is $4,000 with IHCC installation.",
            "Pickup recovery is $2,690 for five days based on two trucks at 10,000 km per truck per month.",
            "Contingency is 3%; corporate-overhead allocation is 10%; target gross-profit margin is 12.5%.",
            "Pipe length is approximately 28 m with 33 m priced.",
            "Plan references conflict between 200 mm and 375 mm PVC SDR35; confirm design size before procurement.",
            "Site markup is a best estimate only and is not a survey; field-verify tie-in, alignment, elevations, utilities, and outlet.",
        ],
        "exclusions": [
            "GST",
            "RFQ issuance or supplier commitment",
            "Bid submission",
            "Unverified design changes, utility conflicts, dewatering, shoring, and contaminated material unless expressly priced",
        ],
    }
    cost_rows = []
    for item in line_items:
        cost = Decimal(str(item["direct_unit_cost"])) * Decimal(str(item["quantity"]))
        cost_rows.append(
            {
                "code": item["code"],
                "description": item["description"],
                "item_type": item["item_type"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "hours": 0.0,
                "labour_cost": 0.0,
                "equipment_cost": 0.0,
                "material_cost": 0.0,
                "disposal_cost": 0.0,
                "subcontract_cost": 0.0,
                "direct_cost": _money(cost),
                "unit_cost": _money(item["direct_unit_cost"]),
                "selected_quote_supplier": None,
                "selected_quote_amount": None,
            }
        )
    summary = {
        "project_name": estimate["project_name"],
        "project_code": DOWNES_PROJECT_NUMBER,
        "direct_cost": _money(direct_cost),
        "indirect_cost": 0.0,
        "risk_cost": 0.0,
        "subtotal_before_markup": _money(direct_cost),
        "contingency": _money(contingency),
        "bonding": 0.0,
        "insurance": 0.0,
        "overhead": _money(overhead),
        "profit": _money(profit),
        "final_price": _money(final_price),
        "gross_margin_percent": 12.5,
        "category_breakdown": {
            "labour": 0.0,
            "equipment": 0.0,
            "material": 0.0,
            "disposal": 0.0,
            "subcontract": 0.0,
            "indirect": 0.0,
            "risk": 0.0,
        },
        "line_items": cost_rows,
        "assumptions": estimate["assumptions"],
        "exclusions": estimate["exclusions"],
    }
    return {"estimate": estimate, "summary": summary}


def _validate() -> dict:
    rows = _load_master()
    records = [_supplier_record(row) for row in rows]
    bad_emails = [email for record in records for email in record["emails"] if not EMAIL_RE.match(email)]
    if bad_emails:
        raise RuntimeError(f"Invalid normalized supplier emails: {bad_emails}")
    downes = _downes_payload()
    if downes["summary"]["final_price"] != 89870.51:
        raise RuntimeError("Downes Road estimate total does not match the approved draft")
    return {
        "status": "validated",
        "supplier_rows": len(records),
        "preferred_suppliers": sum(1 for record in records if record["metadata"]["preferred"]),
        "excluded_bounced_suppliers": sum(1 for record in records if record["metadata"]["status"] == "bounced"),
        "downes_exact_estimate": downes["summary"]["final_price"],
        "downes_recommended_bid_before_gst": 90000.0,
        "rfq_send_enabled": False,
        "bid_submission_enabled": False,
    }


def _reconcile_database() -> dict:
    sys.path.insert(0, "/app")
    from sqlalchemy import delete, func, or_, select

    from app.db.session import SessionLocal
    from app.models.bid import Bid
    from app.models.contact import Contact
    from app.models.project import Project
    from app.models.supplier import Supplier

    records = [_supplier_record(row) for row in _load_master()]
    downes_payload = _downes_payload()
    created = 0
    updated = 0
    contacts_added = 0
    contacts_removed = 0
    smoke_archived = 0

    with SessionLocal() as db:
        for record in records:
            supplier = db.scalar(
                select(Supplier).where(func.lower(Supplier.name) == record["name"].casefold())
            )
            if supplier is None:
                supplier = Supplier(name=record["name"])
                db.add(supplier)
                db.flush()
                created += 1
            else:
                updated += 1
            supplier.category = record["category"]
            supplier.service_area = record["service_area"]
            supplier.website = record["website"]
            supplier.notes = record["notes"]
            existing_metadata = supplier.metadata_json or {}
            supplier.metadata_json = {**existing_metadata, **record["metadata"]}

            for bounced in record["bounced_emails"]:
                result = db.execute(
                    delete(Contact).where(
                        Contact.supplier_id == supplier.id,
                        func.lower(Contact.email) == bounced.casefold(),
                    )
                )
                contacts_removed += result.rowcount or 0

            existing_emails = {
                str(email).casefold()
                for email in db.scalars(
                    select(Contact.email).where(
                        Contact.supplier_id == supplier.id,
                        Contact.email.is_not(None),
                    )
                ).all()
            }
            for email in record["emails"]:
                if email.casefold() in existing_emails:
                    continue
                db.add(
                    Contact(
                        supplier_id=supplier.id,
                        first_name="Estimating",
                        last_name=None,
                        email=email,
                        phone=record["phone"],
                        role="Estimating",
                    )
                )
                contacts_added += 1

        smoke_projects = db.scalars(
            select(Project).where(
                or_(
                    Project.name.ilike("Release smoke %"),
                    Project.project_number.ilike("SMOKE-%"),
                )
            )
        ).all()
        for smoke in smoke_projects:
            if smoke.status != "archived":
                smoke.status = "archived"
                smoke_archived += 1

        project = db.scalar(select(Project).where(Project.project_number == DOWNES_PROJECT_NUMBER))
        if project is None:
            project = db.scalar(
                select(Project).where(Project.name.ilike("Downes Road%"), Project.status != "archived")
            )
        if project is None:
            project = Project(name="Downes Road Drainage Reinstatement")
            db.add(project)
            db.flush()
        project.name = "Downes Road Drainage Reinstatement"
        project.project_number = DOWNES_PROJECT_NUMBER
        project.municipality_name = "Abbotsford"
        project.project_address = "Downes Road at Bradner Road, Abbotsford, BC"
        project.contract_value = Decimal("90000.00")
        project.status = "tendering"
        project.notes = (
            "DRAFT ONLY. No RFQ emails and no bid submission. Confirm conflicting 200 mm/375 mm "
            "PVC SDR35 design reference, tie-in, alignment, elevations, utilities, and outlet before procurement."
        )
        project.metadata_json = {
            **(project.metadata_json or {}),
            "draft_only": True,
            "rfq_send_enabled": False,
            "bid_submission_enabled": False,
            "estimate_exact_before_gst": 89870.51,
            "recommended_bid_before_gst": 90000.0,
            "target_gross_margin_percent": 12.5,
            "contingency_percent": 3.0,
            "corporate_overhead_percent": 10.0,
            "headwall_allowance": 4000.0,
            "pickup_recovery_five_days": 2690.0,
            "pipe_length_priced_m": 33,
            "pipe_size_status": "conflict_200mm_vs_375mm_confirm_before_procurement",
        }

        current_workspace = None
        for bid in db.scalars(select(Bid).where(Bid.project_id == project.id)).all():
            source = (bid.bid_json or {}).get("source")
            if source == DOWNES_ESTIMATE_SOURCE:
                current_workspace = bid
            elif bid.total_amount is not None and Decimal(str(bid.total_amount)) == Decimal("122000.00"):
                bid.status = "superseded"
        if current_workspace is None:
            current_workspace = Bid(project_id=project.id)
            db.add(current_workspace)
        current_workspace.status = "draft"
        current_workspace.total_amount = Decimal("89870.51")
        current_workspace.summary = (
            "Draft estimate $89,870.51; recommended bid $90,000 before GST; "
            "12.5% gross-profit margin. RFQs and submission are locked."
        )
        current_workspace.bid_json = {
            "estimate": downes_payload["estimate"],
            "summary": downes_payload["summary"],
            "source": DOWNES_ESTIMATE_SOURCE,
            "controls": {"rfq_send_enabled": False, "bid_submission_enabled": False},
        }

        db.commit()
        total_suppliers = db.scalar(select(func.count()).select_from(Supplier)) or 0
        project_id = str(project.id)
        workspace_id = str(current_workspace.id)

    return {
        "status": "completed",
        "supplier_master_rows": len(records),
        "suppliers_created": created,
        "suppliers_updated": updated,
        "supplier_contacts_added": contacts_added,
        "known_bounced_contacts_removed": contacts_removed,
        "total_suppliers_in_database": total_suppliers,
        "release_smoke_projects_archived": smoke_archived,
        "downes_project_id": project_id,
        "downes_estimate_workspace_id": workspace_id,
        "downes_exact_estimate": 89870.51,
        "downes_recommended_bid_before_gst": 90000.0,
        "rfq_send_enabled": False,
        "bid_submission_enabled": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate files without opening the database")
    args = parser.parse_args()
    result = _validate() if args.dry_run else _reconcile_database()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
