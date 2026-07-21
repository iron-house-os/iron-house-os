#!/usr/bin/env python3
"""Idempotently stage TFN RFP 2026-003 in Iron House OS.

The action updates the user's existing TFN project when present, registers the
authoritative Drive tender package, records the owner-supplied quantity schedule,
creates a provisional estimate using the current Iron House estimating controls,
and prepares draft-only RFQ scopes. It never sends an RFQ or submits a bid.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


PROJECT_CODE = "TFN-2026-003"
TENDER_NUMBER = "2026-003"
ESTIMATE_SOURCE = "tfn-rfp-2026-003-budget-v1-2026-07-21"
DRIVE_FILE_ID = "1n54gmRDDvse6NToVx8Fue6MRLNhYlgsW"
DRIVE_URL = f"https://drive.google.com/file/d/{DRIVE_FILE_ID}/view"
PACKAGE_NAME = "RFP_2026-003_Construction_Services_for_MUP.pdf"
MONEY = Decimal("0.01")


QUANTITIES = [
    {"code": "A.1", "description": "Mobilization and demobilization", "unit": "LS", "quantity": 1, "direct_unit_cost": 180000, "item_type": "indirect", "confidence": "medium", "rfq_scope": "general_conditions"},
    {"code": "A.2", "description": "Erosion and sediment control including dust control", "unit": "LS", "quantity": 1, "direct_unit_cost": 65000, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "environmental"},
    {"code": "A.3", "description": "Traffic control, vehicle access and parking", "unit": "LS", "quantity": 1, "direct_unit_cost": 140000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "traffic_control"},
    {"code": "A.4", "description": "Strip topsoil and dispose offsite", "unit": "m3", "quantity": 1150, "direct_unit_cost": 48, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "aggregate_trucking"},
    {"code": "A.5", "description": "Place and compact fill", "unit": "m3", "quantity": 815, "direct_unit_cost": 62, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "aggregate_trucking"},
    {"code": "B.1", "description": "Asphalt removal", "unit": "m2", "quantity": 1100, "direct_unit_cost": 28, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "aggregate_trucking"},
    {"code": "B.2", "description": "Bus stop shelter removal", "unit": "LS", "quantity": 1, "direct_unit_cost": 15000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "translink_bus_shelter"},
    {"code": "B.3", "description": "Stamped concrete speed hump", "unit": "m2", "quantity": 5, "direct_unit_cost": 750, "item_type": "subcontract", "confidence": "low", "rfq_scope": "concrete"},
    {"code": "B.4", "description": "150 mm thick bus shelter concrete slab", "unit": "m2", "quantity": 4, "direct_unit_cost": 700, "item_type": "subcontract", "confidence": "low", "rfq_scope": "concrete"},
    {"code": "B.5", "description": "300 mm granular subbase", "unit": "m2", "quantity": 2060, "direct_unit_cost": 42, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "aggregate_trucking"},
    {"code": "B.6", "description": "75 mm pitrun granular subbase", "unit": "m2", "quantity": 350, "direct_unit_cost": 18, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "aggregate_trucking"},
    {"code": "B.7", "description": "100 mm granular base course", "unit": "m2", "quantity": 2470, "direct_unit_cost": 25, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "aggregate_trucking"},
    {"code": "B.8", "description": "50 mm thick HMAC", "unit": "m2", "quantity": 290, "direct_unit_cost": 58, "item_type": "subcontract", "confidence": "low", "rfq_scope": "asphalt"},
    {"code": "B.9", "description": "85 mm thick HMAC in two lifts", "unit": "m2", "quantity": 2945, "direct_unit_cost": 58, "item_type": "subcontract", "confidence": "low", "rfq_scope": "asphalt"},
    {"code": "B.10", "description": "Asphalt mill and overlay", "unit": "m2", "quantity": 166, "direct_unit_cost": 82, "item_type": "subcontract", "confidence": "low", "rfq_scope": "asphalt"},
    {"code": "B.11", "description": "Paint line eradication", "unit": "m", "quantity": 425, "direct_unit_cost": 9, "item_type": "subcontract", "confidence": "low", "rfq_scope": "markings_signage"},
    {"code": "B.12", "description": "Thermoplastic line painting", "unit": "m", "quantity": 1570, "direct_unit_cost": 16, "item_type": "subcontract", "confidence": "low", "rfq_scope": "markings_signage"},
    {"code": "B.13", "description": "Thermoplastic pavement markings", "unit": "LS", "quantity": 1, "direct_unit_cost": 24000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "markings_signage"},
    {"code": "B.14", "description": "Green MMA solid pavement markings", "unit": "LS", "quantity": 1, "direct_unit_cost": 35000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "markings_signage"},
    {"code": "B.15", "description": "Bike lane concrete barrier", "unit": "EA", "quantity": 286, "direct_unit_cost": 825, "item_type": "subcontract", "confidence": "low", "rfq_scope": "road_safety"},
    {"code": "B.16", "description": "Flexible delineator mounted to concrete barrier", "unit": "EA", "quantity": 150, "direct_unit_cost": 260, "item_type": "subcontract", "confidence": "low", "rfq_scope": "road_safety"},
    {"code": "B.17", "description": "Signage relocation", "unit": "EA", "quantity": 9, "direct_unit_cost": 1500, "item_type": "subcontract", "confidence": "low", "rfq_scope": "markings_signage"},
    {"code": "B.18", "description": "Community mailbox relocation", "unit": "LS", "quantity": 1, "direct_unit_cost": 10000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "specialty_relocations"},
    {"code": "B.19", "description": "Wheel stop relocation", "unit": "EA", "quantity": 13, "direct_unit_cost": 500, "item_type": "subcontract", "confidence": "low", "rfq_scope": "concrete"},
    {"code": "B.20", "description": "TransLink bus stop shelter", "unit": "LS", "quantity": 1, "direct_unit_cost": 75000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "translink_bus_shelter"},
    {"code": "B.21", "description": "Lock block retaining wall", "unit": "LS", "quantity": 1, "direct_unit_cost": 285000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "retaining_wall_handrail"},
    {"code": "B.22", "description": "Handrails", "unit": "m", "quantity": 290, "direct_unit_cost": 725, "item_type": "subcontract", "confidence": "low", "rfq_scope": "retaining_wall_handrail"},
    {"code": "C.1", "description": "Adjust valve lid", "unit": "EA", "quantity": 1, "direct_unit_cost": 2500, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "pipe_structures"},
    {"code": "C.2", "description": "Regrade ditch", "unit": "m", "quantity": 725, "direct_unit_cost": 48, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "aggregate_trucking"},
    {"code": "C.3", "description": "150 mm PVC storm drain", "unit": "m", "quantity": 21, "direct_unit_cost": 650, "item_type": "self_perform", "confidence": "medium", "rfq_scope": "pipe_structures"},
    {"code": "C.4", "description": "600 mm lawn basin", "unit": "EA", "quantity": 1, "direct_unit_cost": 8500, "item_type": "self_perform", "confidence": "low", "rfq_scope": "pipe_structures"},
    {"code": "D.1", "description": "Adjust hydro infrastructure manhole lid", "unit": "LS", "quantity": 1, "direct_unit_cost": 20000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "electrical_utility"},
    {"code": "E.1", "description": "Topsoil supply and placement", "unit": "m3", "quantity": 1460, "direct_unit_cost": 72, "item_type": "self_perform", "confidence": "low", "rfq_scope": "landscaping"},
    {"code": "E.2", "description": "Sodding", "unit": "m2", "quantity": 1460, "direct_unit_cost": 24, "item_type": "subcontract", "confidence": "low", "rfq_scope": "landscaping"},
    {"code": "E.3", "description": "Shrub planter including five-year maintenance", "unit": "EA", "quantity": 11, "direct_unit_cost": 7500, "item_type": "subcontract", "confidence": "low", "rfq_scope": "landscaping"},
    {"code": "E.4", "description": "Memorial tree removal, chipping and delivery", "unit": "LS", "quantity": 1, "direct_unit_cost": 15000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "landscaping"},
    {"code": "E.5", "description": "Replacement Douglas Fir including five-year maintenance", "unit": "EA", "quantity": 1, "direct_unit_cost": 45000, "item_type": "subcontract", "confidence": "low", "rfq_scope": "landscaping"},
]


RFQ_SCOPES = [
    {"key": "aggregate_trucking", "title": "TFN - Aggregates, trucking and disposal", "categories": ["Aggregates", "Trucking", "Disposal"], "codes": ["A.4", "A.5", "B.1", "B.5", "B.6", "B.7", "C.2", "E.1"]},
    {"key": "asphalt", "title": "TFN - Asphalt paving, milling and restoration", "categories": ["Asphalt"], "codes": ["B.8", "B.9", "B.10"]},
    {"key": "concrete", "title": "TFN - Concrete and wheel-stop work", "categories": ["Concrete"], "codes": ["B.3", "B.4", "B.19"]},
    {"key": "traffic_control", "title": "TFN - Traffic management and control", "categories": ["Traffic Control"], "codes": ["A.3"]},
    {"key": "markings_signage", "title": "TFN - Pavement markings and signage", "categories": ["Traffic Control", "Line Painting"], "codes": ["B.11", "B.12", "B.13", "B.14", "B.17"]},
    {"key": "road_safety", "title": "TFN - Bike barriers and delineators", "categories": ["Traffic Control", "Road Safety"], "codes": ["B.15", "B.16"]},
    {"key": "retaining_wall_handrail", "title": "TFN - Lock-block wall and handrail", "categories": ["Concrete", "Retaining Wall", "Metal Fabrication"], "codes": ["B.21", "B.22"]},
    {"key": "pipe_structures", "title": "TFN - Storm pipe and lawn basin materials", "categories": ["Waterworks / Pipe", "Precast Concrete"], "codes": ["C.1", "C.3", "C.4"]},
    {"key": "translink_bus_shelter", "title": "TFN - TransLink bus shelter work", "categories": ["Transit", "Concrete"], "codes": ["B.2", "B.20"]},
    {"key": "landscaping", "title": "TFN - Landscaping and five-year plant maintenance", "categories": ["Landscaping", "Topsoil"], "codes": ["E.1", "E.2", "E.3", "E.4", "E.5"]},
    {"key": "electrical_utility", "title": "TFN - Hydro infrastructure adjustment", "categories": ["Electrical", "Utilities"], "codes": ["D.1"]},
    {"key": "testing_survey_environmental", "title": "TFN - Testing, survey and environmental support", "categories": ["Geotechnical / Testing", "Survey", "Environmental"], "codes": []},
]


RFQ_NAME_HINTS = {
    "aggregate_trucking": ["amrize", "lafarge", "lehigh", "heidelberg", "universal trucking", "aggregate", "gravel"],
    "asphalt": ["superior paving", "winvan", "ba blacktop", "lafarge", "asphalt", "paving"],
    "concrete": ["jws concrete", "amrize", "concrete"],
    "traffic_control": ["traffic"],
    "markings_signage": ["marking", "line painting", "sign"],
    "road_safety": ["traffic", "barrier", "delineator", "sign"],
    "retaining_wall_handrail": ["lock block", "retaining", "concrete", "fabrication", "rail"],
    "pipe_structures": ["emco", "sheret", "iconix", "wolseley", "delta irrigation", "southern irrigation", "pipe", "waterworks"],
    "translink_bus_shelter": ["transit", "bus shelter", "concrete"],
    "landscaping": ["landscape", "topsoil", "sod", "nursery", "tree"],
    "electrical_utility": ["electrical", "hydro", "utility"],
    "testing_survey_environmental": ["advanced testing", "geopacific", "testing", "survey", "environmental", "geotechnical"],
}


RISKS = [
    {"rating": "critical", "risk": "Surety letter and 50% performance/payment bonds are mandatory", "action": "Confirm bonding capacity before bid commitment."},
    {"rating": "critical", "risk": "Corporate experience, three comparable references and full-time superintendent are evaluated", "action": "Complete readiness review before submission."},
    {"rating": "high", "risk": "Two phases with winter remobilization and concurrent lift-station work", "action": "Carry remobilization and issue a phased baseline schedule."},
    {"rating": "high", "risk": "No compensation for permit, utility, inspection or bird-nesting delays", "action": "Price standby exposure and preserve notice records."},
    {"rating": "high", "risk": "Lock-block wall, bus shelter and MMA markings are lump-sum with incomplete measurable detail", "action": "Obtain specialist quotes and verify drawings."},
    {"rating": "high", "risk": "Plant establishment, watering, replacement and warranty extend five years", "action": "Require a five-year landscaping quote and maintenance plan."},
    {"rating": "high", "risk": "Payment can extend to about 50 calendar days after a complete progress claim", "action": "Model working capital and LOC exposure."},
    {"rating": "medium", "risk": "Groundwater is about 1.5 m below grade with possible perched water", "action": "Carry conventional pumping and verify storm depth."},
    {"rating": "medium", "risk": "Road closures are prohibited and residential access must be maintained", "action": "Validate TMP assumptions at site meeting."},
    {"rating": "medium", "risk": "Liquefaction and settlement monitoring plus geotechnical field reviews are required", "action": "Confirm testing responsibility and quote frequency."},
    {"rating": "medium", "risk": "TFN member engagement can influence best-value evaluation", "action": "Seek eligible TFN subcontracting, employment or purchasing participation."},
]


ASSUMPTIONS = [
    "Budget estimate only; supplier and subcontractor quotations have not yet been incorporated.",
    "Current estimating controls: 3% contingency, 10% corporate overhead and 12.5% target gross-profit margin.",
    "Bonding allowance is 1.5% and project-specific insurance allowance is 0.75%, both pending broker/surety confirmation.",
    "Two-pickup recovery is $10,760 per month for 5.5 active months ($59,180), based on 10,000 km per truck per month.",
    "Iron House self-performs excavation, stripping, fill, granular placement, drainage, ditching, topsoil placement and cleanup with rented major equipment.",
    "Asphalt, traffic control, concrete finishing, markings, walls/handrails, electrical adjustment, bus shelter and specialty landscape work are subcontracted.",
    "Tender quantities in Appendix H are the controlling first-pass quantities; drawing takeoff remains subject to visual verification.",
    "Pricing excludes GST and remains draft-only. RFQ sending and bid submission are disabled.",
]


EXCLUSIONS = [
    "GST",
    "Unidentified contaminated soil or hazardous material",
    "Extraordinary dewatering or engineered shoring not shown in the tender documents",
    "Utility betterments beyond adjustments explicitly shown",
    "Owner-directed scope additions after the tender closing date",
]


def money(value: Decimal | float | int | str) -> float:
    return float(Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP))


def build_payload() -> dict:
    direct = sum(Decimal(str(row["quantity"])) * Decimal(str(row["direct_unit_cost"])) for row in QUANTITIES)
    pickup = Decimal("59180")
    subtotal = direct + pickup
    contingency = subtotal * Decimal("0.03")
    bonding = (subtotal + contingency) * Decimal("0.015")
    insurance = (subtotal + contingency + bonding) * Decimal("0.0075")
    overhead = (subtotal + contingency + bonding + insurance) * Decimal("0.10")
    pre_profit = subtotal + contingency + bonding + insurance + overhead
    profit = pre_profit * Decimal("0.125") / Decimal("0.875")
    final = pre_profit + profit
    allocation_factor = final / direct

    line_items = []
    schedule_prices = []
    for row in QUANTITIES:
        direct_amount = Decimal(str(row["quantity"])) * Decimal(str(row["direct_unit_cost"]))
        line_items.append({
            "code": row["code"],
            "description": row["description"],
            "item_type": row["item_type"],
            "quantity": row["quantity"],
            "unit": row["unit"],
            "direct_unit_cost": row["direct_unit_cost"],
            "notes": f"Appendix H quantity; {row['confidence']} confidence budget rate; RFQ scope {row['rfq_scope']}.",
        })
        all_in_amount = direct_amount * allocation_factor
        schedule_prices.append({
            "code": row["code"],
            "description": row["description"],
            "unit": row["unit"],
            "quantity": row["quantity"],
            "budget_direct_unit_cost": money(row["direct_unit_cost"]),
            "budget_direct_amount": money(direct_amount),
            "provisional_all_in_unit_price": money(all_in_amount / Decimal(str(row["quantity"]))),
            "provisional_all_in_amount": money(all_in_amount),
            "confidence": row["confidence"],
        })

    estimate = {
        "project_name": "TFN Multi-Use Pathway on Tsawwassen Drive",
        "project_code": PROJECT_CODE,
        "owner": "Tsawwassen First Nation",
        "estimator": "Iron House Civil Constructors",
        "line_items": line_items,
        "indirects": [{"description": "Two-pickup fleet recovery - 5.5 active months", "amount": 59180, "category": "fleet"}],
        "risks": [],
        "markup": {"contingency_percent": 3.0, "bonding_percent": 1.5, "insurance_percent": 0.75, "overhead_percent": 10.0, "profit_percent": 14.285714},
        "assumptions": ASSUMPTIONS,
        "exclusions": EXCLUSIONS,
    }
    summary = {
        "project_name": estimate["project_name"],
        "project_code": PROJECT_CODE,
        "direct_cost": money(direct),
        "indirect_cost": money(pickup),
        "subtotal_before_markup": money(subtotal),
        "contingency": money(contingency),
        "bonding": money(bonding),
        "insurance": money(insurance),
        "overhead": money(overhead),
        "profit": money(profit),
        "final_price": money(final),
        "recommended_bid_before_gst": 3030000.0,
        "gross_margin_percent": 12.5,
        "schedule_prices": schedule_prices,
        "assumptions": ASSUMPTIONS,
        "exclusions": EXCLUSIONS,
        "confidence": "budget_low",
        "bid_readiness": "conditional_no_go_until_surety_references_superintendent_and_quotes_confirmed",
    }
    return {"estimate": estimate, "summary": summary}


def validate() -> dict:
    payload = build_payload()
    assert len(QUANTITIES) == 37
    assert payload["summary"]["direct_cost"] == 2224147.0
    assert payload["summary"]["indirect_cost"] == 59180.0
    assert payload["summary"]["final_price"] == 3023437.99
    assert len(RFQ_SCOPES) == 12
    return {
        "status": "validated",
        "tender": TENDER_NUMBER,
        "quantity_items": len(QUANTITIES),
        "draft_rfq_scopes": len(RFQ_SCOPES),
        "budget_estimate_before_gst": payload["summary"]["final_price"],
        "recommended_budget_before_gst": payload["summary"]["recommended_bid_before_gst"],
        "target_gross_margin_percent": 12.5,
        "rfq_send_enabled": False,
        "bid_submission_enabled": False,
    }


def reconcile_database() -> dict:
    sys.path.insert(0, "/app")
    from sqlalchemy import func, or_, select

    from app.db.session import SessionLocal
    from app.models.bid import Bid
    from app.models.document import Document, Drawing, Takeoff
    from app.models.project import Project
    from app.models.rfq import RFQ, RFQPackage, RFQPackageSupplierRecipient
    from app.models.supplier import Supplier
    from app.models.tender import Tender

    payload = build_payload()
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.project_number == PROJECT_CODE))
        if project is None:
            project = db.scalar(select(Project).where(func.lower(Project.name) == "tfn"))
        if project is None:
            project = db.scalar(select(Project).where(Project.name.ilike("TFN%"), Project.status != "archived"))
        project_created = project is None
        if project is None:
            project = Project(name="TFN")
            db.add(project)
            db.flush()

        project.name = "TFN - Multi-Use Pathway on Tsawwassen Drive"
        project.client_owner = "Tsawwassen First Nation"
        project.municipality_name = "Tsawwassen First Nation"
        project.project_number = PROJECT_CODE
        project.tender_number = TENDER_NUMBER
        project.tender_source = "BC Bid / Google Drive tender package"
        project.tender_closing_date = date(2026, 8, 11)
        project.bid_due_date = date(2026, 8, 11)
        project.estimated_construction_start = date(2026, 9, 1)
        project.estimated_construction_finish = date(2027, 5, 31)
        project.project_address = "Tsawwassen Drive, Blue Heron Way to Falcon Way, Tsawwassen, BC"
        project.contract_value = Decimal("3030000.00")
        project.status = "tendering"
        project.description = "Construction of a multi-use pathway, roadway widening, drainage, retaining wall, handrails, bus-stop improvements, markings and landscaping."
        project.notes = "DRAFT BID PROCESS. No RFQs may be sent and no bid may be submitted without explicit approval."
        project.metadata_json = {
            **(project.metadata_json or {}),
            "draft_only": True,
            "rfq_send_enabled": False,
            "bid_submission_enabled": False,
            "site_meeting": "2026-07-23T10:30:00-07:00",
            "site_meeting_location": "Tsawwassen Drive and Falcon Way",
            "question_deadline": "2026-08-04",
            "closing": "2026-08-11T14:00:00-07:00",
            "substantial_completion": "2027-05-31",
            "phase_1": "September 2026 - sportsfield entrance to lift-station worksite",
            "phase_2": "Mid-February through May 2027 - Blue Heron Way to lift-station worksite",
            "target_gross_margin_percent": 12.5,
            "contingency_percent": 3.0,
            "corporate_overhead_percent": 10.0,
            "pickup_recovery": 59180.0,
            "bonding_percent": 1.5,
            "insurance_percent": 0.75,
            "budget_estimate_before_gst": payload["summary"]["final_price"],
            "recommended_budget_before_gst": 3030000.0,
            "bid_readiness": payload["summary"]["bid_readiness"],
            "addenda_checked_at": "2026-07-21",
            "addenda_status": "none_confirmed_in_package_or_public_search_monitor_bc_bid",
            "source_drive_file_id": DRIVE_FILE_ID,
        }

        tender = db.scalar(select(Tender).where(Tender.tender_number == TENDER_NUMBER))
        if tender is None:
            tender = Tender(title="Construction Services for Multi-Use Pathway on Tsawwassen Drive")
            db.add(tender)
        tender.project_id = project.id
        tender.title = "Construction Services for Multi-Use Pathway on Tsawwassen Drive"
        tender.tender_number = TENDER_NUMBER
        tender.source = "BC Bid"
        tender.source_url = DRIVE_URL
        tender.owner = "Tsawwassen First Nation"
        tender.municipality_name = "Tsawwassen First Nation"
        tender.closing_date = date(2026, 8, 11)
        tender.site_meeting_date = date(2026, 7, 23)
        tender.question_deadline = date(2026, 8, 4)
        tender.project_address = project.project_address
        tender.description = project.description
        tender.status = "estimating"
        tender.estimated_value = Decimal("3030000.00")
        tender.metadata_json = {"closing_time_pst": "14:00", "site_meeting_time_pst": "10:30", "contract": "CCDC 4-2011 unit price", "bid_validity_days": 60, "performance_bond_percent": 50, "labour_material_bond_percent": 50}
        db.flush()

        document = db.scalar(select(Document).where(Document.project_id == project.id, Document.metadata_json["drive_file_id"].as_string() == DRIVE_FILE_ID))
        if document is None:
            document = db.scalar(select(Document).where(Document.project_id == project.id, Document.title == PACKAGE_NAME))
        if document is None:
            document = Document(title=PACKAGE_NAME, category="tender_package")
            db.add(document)
        document.project_id = project.id
        document.tender_id = tender.id
        document.status = "registered_external"
        document.storage_uri = DRIVE_URL
        document.description = "Authoritative 121 MB RFP package from the TFN path folder in Google Drive."
        document.issue_date = date(2026, 7, 20)
        document.metadata_json = {"drive_file_id": DRIVE_FILE_ID, "size_bytes": 120978155, "source": "Google Drive", "contains": ["RFP", "scope", "drawings", "CEMP", "CCDC 4", "supplementary conditions", "MMCD supplements", "quantity schedule", "proposal form", "geotechnical report", "topographic survey", "procurement policy"]}

        drawing = db.scalar(select(Drawing).where(Drawing.project_id == project.id, Drawing.title == "TFN MUP tender drawings - Appendix C"))
        if drawing is None:
            drawing = Drawing(project_id=project.id, title="TFN MUP tender drawings - Appendix C")
            db.add(drawing)
        drawing.discipline = "Civil / Landscape"
        drawing.storage_uri = DRIVE_URL
        drawing.metadata_json = {"source_document": PACKAGE_NAME, "status": "visual_verification_required", "quantity_source": "Appendix H"}
        db.flush()

        takeoff = db.scalar(select(Takeoff).where(Takeoff.project_id == project.id, Takeoff.notes == ESTIMATE_SOURCE))
        if takeoff is None:
            takeoff = Takeoff(project_id=project.id, drawing_id=drawing.id)
            db.add(takeoff)
        takeoff.status = "review_required"
        takeoff.notes = ESTIMATE_SOURCE
        takeoff.quantities_json = {"source": "Appendix H - Schedule of Quantities and Prices", "items": [{k: row[k] for k in ("code", "description", "unit", "quantity", "confidence", "rfq_scope")} for row in QUANTITIES], "drawing_measurement_status": "pending_visual_cross_check"}

        bid = None
        for candidate in db.scalars(select(Bid).where(Bid.project_id == project.id)).all():
            if (candidate.bid_json or {}).get("source") == ESTIMATE_SOURCE:
                bid = candidate
                break
        if bid is None:
            bid = Bid(project_id=project.id, tender_id=tender.id)
            db.add(bid)
        bid.status = "draft"
        bid.total_amount = Decimal(str(payload["summary"]["final_price"]))
        bid.summary = "Budget draft $3,023,437.99; recommended working bid $3,030,000 before GST; 12.5% target gross margin. Conditional no-go pending surety, references, superintendent, site review and firm quotes."
        bid.bid_json = {"source": ESTIMATE_SOURCE, "estimate": payload["estimate"], "summary": payload["summary"], "risks": RISKS, "controls": {"rfq_send_enabled": False, "bid_submission_enabled": False}}

        rfq_created = 0
        package_created = 0
        recipients_created = 0
        due_at = datetime(2026, 7, 30, 17, 0, tzinfo=timezone.utc)
        item_by_code = {row["code"]: row for row in QUANTITIES}
        suppliers = db.scalars(select(Supplier)).all()
        for scope in RFQ_SCOPES:
            scoped_items = [{k: item_by_code[code][k] for k in ("code", "description", "unit", "quantity")} for code in scope["codes"]]
            rfq = db.scalar(select(RFQ).where(RFQ.project_id == project.id, RFQ.title == scope["title"]))
            if rfq is None:
                rfq = RFQ(project_id=project.id, title=scope["title"])
                db.add(rfq)
                rfq_created += 1
            rfq.status = "draft_locked"
            rfq.due_at = due_at
            rfq.scope_summary = "; ".join(f"{i['code']} {i['description']} - {i['quantity']} {i['unit']}" for i in scoped_items) or "Quote testing, survey and environmental support required by the tender documents."
            rfq.package_json = {"scope_key": scope["key"], "items": scoped_items, "supplier_category_targets": scope["categories"], "source_document": DRIVE_URL, "quote_due": "2026-07-30", "send_enabled": False, "attachments_required": ["Appendix C drawings", "applicable specifications", "Appendix H scope extract"]}

            package = db.scalar(select(RFQPackage).where(RFQPackage.project_id == project.id, RFQPackage.title == scope["title"]))
            if package is None:
                package = RFQPackage(project_id=project.id, title=scope["title"])
                db.add(package)
                package_created += 1
            package.project_name = project.name
            package.scope_summary = rfq.scope_summary
            package.due_at = due_at
            package.status = "draft_locked"
            package.supplier_category_targets = scope["categories"]
            package.metadata_json = {"scope_key": scope["key"], "line_item_codes": scope["codes"], "send_enabled": False, "source_drive_file_id": DRIVE_FILE_ID}
            db.flush()

            hints = RFQ_NAME_HINTS[scope["key"]]
            ranked = []
            for supplier in suppliers:
                metadata = supplier.metadata_json or {}
                if str(metadata.get("status") or "").lower() in {"bounced", "do_not_use"}:
                    continue
                haystack = " ".join([supplier.name or "", supplier.category or "", supplier.notes or ""]).casefold()
                score = sum(3 if hint in (supplier.name or "").casefold() else 1 for hint in hints if hint in haystack)
                if metadata.get("preferred"):
                    score += 2
                if score:
                    ranked.append((score, supplier.name.casefold(), supplier))
            ranked.sort(key=lambda value: (-value[0], value[1]))
            for _, _, supplier in ranked[:5]:
                recipient = db.scalar(select(RFQPackageSupplierRecipient).where(RFQPackageSupplierRecipient.rfq_package_id == package.id, RFQPackageSupplierRecipient.supplier_id == str(supplier.id)))
                if recipient is None:
                    recipient = RFQPackageSupplierRecipient(rfq_package_id=package.id, supplier_id=str(supplier.id), supplier_name=supplier.name)
                    db.add(recipient)
                    recipients_created += 1
                recipient.category = supplier.category
                recipient.status = "selected_draft"

        db.commit()
        result = validate()
        result.update({"status": "completed", "project_created": project_created, "project_id": str(project.id), "tender_id": str(tender.id), "bid_id": str(bid.id), "takeoff_id": str(takeoff.id), "rfqs_created": rfq_created, "rfq_packages_created": package_created, "draft_recipients_created": recipients_created})
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = validate() if args.dry_run else reconcile_database()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
