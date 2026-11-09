"""Controlled historical staging intake for the Fernie 2026 bid package.

The tender closing date has passed. The importer preserves the package as a
historical opportunity with an explicitly unverified submission outcome; it
must not present the record as an active bid.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.bid import Bid
from app.models.document import Document
from app.models.project import Project
from app.models.rfq import RFQPackage, RFQPackageDocument
from app.models.tender import Tender
from app.services.drive_tender_import import (
    ImportValidationError,
    TenderFolder,
    import_drive_tenders,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

SOURCE_KEY = "fernie_2026_bid_package"
FERNIE_FOLDER_IDS = frozenset(
    {
        "1x8jdyiBthezgTOHUrluRJXy8AHff9vaT",
        "1dA9BCow-rTCqivIR0lZ-GcS4lTciN8MT",
    }
)
FERNIE_TITLE = "City of Fernie - 2026 Sanitary Manhole Infiltration Repair Program"
FERNIE_SOURCE_URL = "https://drive.google.com/drive/folders/1x8jdyiBthezgTOHUrluRJXy8AHff9vaT"
FERNIE_CLOSING_DATE = date(2026, 8, 14)
FERNIE_CLOSING_AT = datetime(2026, 8, 14, 20, 0, tzinfo=timezone.utc)
FERNIE_VALUE = Decimal("169500.00")
FERNIE_SCOPE = (
    "Repair 11 active sanitary manholes using targeted injection grouting, "
    "temporary groundwater drawdown, confined-space controls, verification, "
    "reporting, and a one-year warranty."
)
SUPPLIER_CATEGORIES = [
    "civil general contractor",
    "earthworks",
    "pipe and fittings",
    "supplier quotes",
    "dewatering and grouting specialty",
]
ALLOWANCES = {
    "av_278": {
        "quantity": "14 x 5-gallon pails",
        "liquid_resin_us_gal": 70,
        "preliminary_usd_low": 7000,
        "preliminary_usd_high": 9100,
        "quote_required": True,
    },
    "temporary_well_points": "8-inch slotted",
    "pipe": {"length_ft": 190, "rate_cad_per_ft": 50, "amount_cad": 9500, "provisional": True},
    "slotting_filter_rock_caps_fittings_cad": 1500,
    "grout_pump_cad": 352.99,
    "dewatering_and_pump_subtotal_cad": 11352.99,
    "dewatering_and_pump_per_manhole_cad": 1032.09,
}


def select_fernie_folders(folders: Sequence[TenderFolder]) -> tuple[TenderFolder, ...]:
    selected = tuple(folder for folder in folders if folder.drive_folder_id in FERNIE_FOLDER_IDS)
    found = {folder.drive_folder_id for folder in selected}
    missing = sorted(FERNIE_FOLDER_IDS - found)
    if missing:
        raise ImportValidationError(f"Fernie manifest is missing source folders: {', '.join(missing)}")
    return selected


def import_fernie_bid_package(
    db: Session,
    folders: Sequence[TenderFolder],
    *,
    actor: str,
    apply: bool = False,
    imported_at: datetime | None = None,
) -> dict[str, object]:
    actor = actor.strip()
    if not actor:
        raise ImportValidationError("An audit actor is required.")
    selected = select_fernie_folders(folders)
    timestamp = (imported_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    project_before = _find_project(db)
    tender_before = _find_tender(db, project_before)
    rfq_before = _find_rfq_package(db, project_before, tender_before)
    bid_before = _find_bid(db, project_before, tender_before)

    base_report = import_drive_tenders(
        db,
        selected,
        actor=actor,
        apply=apply,
        imported_at=imported_at,
    )
    report: dict[str, object] = {
        "status": "applied" if apply else "dry_run",
        "historical_intake": True,
        "closing_date": FERNIE_CLOSING_DATE.isoformat(),
        "closing_passed": True,
        "submission_status": "unverified",
        "source_folder_ids": sorted(FERNIE_FOLDER_IDS),
        "source_file_count": sum(len(folder.files) for folder in selected),
        "drive_import": base_report,
        "objects": {
            "project": "update" if project_before else "create",
            "tender": "update" if tender_before else "create",
            "rfq_package": "update" if rfq_before else "create",
            "bid_workspace": "update" if bid_before else "create",
        },
    }
    if not apply:
        return report

    project = _find_project(db)
    if project is None:
        raise ImportValidationError(
            "Fernie project was not created because the Drive import was ambiguous; review the dry-run report."
        )

    project.name = FERNIE_TITLE
    project.client_owner = "City of Fernie"
    project.municipality_name = "Fernie, BC"
    project.tender_source = "City of Fernie RFP"
    project.tender_closing_date = FERNIE_CLOSING_DATE
    project.bid_due_date = FERNIE_CLOSING_DATE
    project.contract_value = FERNIE_VALUE
    project.status = "opportunity"
    project.notes = FERNIE_SCOPE
    project.metadata_json = {
        **(project.metadata_json or {}),
        SOURCE_KEY: _source_metadata(actor, timestamp, selected),
    }
    db.flush()

    rfq_package = _upsert_rfq_package(db, project, tender_before, actor, timestamp)
    tender = _upsert_tender(db, project, rfq_package, actor, timestamp)
    bid = _upsert_bid(db, project, tender, actor, timestamp)
    linked_document_count, rfq_document_count = _link_documents(
        db,
        project,
        tender,
        rfq_package,
        selected,
    )
    db.flush()

    report.update(
        {
            "project_id": str(project.id),
            "tender_id": str(tender.id),
            "rfq_package_id": str(rfq_package.id),
            "bid_id": str(bid.id),
            "linked_document_count": linked_document_count,
            "rfq_document_count": rfq_document_count,
            "project_status": project.status,
            "tender_status": tender.status,
            "bid_status": bid.status,
        }
    )
    return report


def _find_project(db: Session) -> Project | None:
    matches: list[Project] = []
    for project in db.scalars(select(Project)).all():
        metadata = project.metadata_json or {}
        source = metadata.get("drive_tender_import", {}) if isinstance(metadata, Mapping) else {}
        folder_ids = set(source.get("source_folder_ids", [])) if isinstance(source, Mapping) else set()
        if folder_ids & FERNIE_FOLDER_IDS or project.name == FERNIE_TITLE:
            matches.append(project)
    if len(matches) > 1:
        raise ImportValidationError("Multiple IHOS projects match the Fernie package.")
    return matches[0] if matches else None


def _find_tender(db: Session, project: Project | None) -> Tender | None:
    if project is None:
        return None
    matches = list(db.scalars(select(Tender).where(Tender.project_id == project.id)).all())
    if len(matches) > 1:
        sourced = [item for item in matches if (item.metadata_json or {}).get("source") == SOURCE_KEY]
        if len(sourced) == 1:
            return sourced[0]
        raise ImportValidationError("Multiple tender records match the Fernie project.")
    return matches[0] if matches else None


def _find_rfq_package(
    db: Session,
    project: Project | None,
    tender: Tender | None,
) -> RFQPackage | None:
    if project is None:
        return None
    if tender is not None and tender.rfq_package_id is not None:
        linked = db.get(RFQPackage, tender.rfq_package_id)
        if linked is not None:
            return linked
    matches = [
        item
        for item in db.scalars(select(RFQPackage).where(RFQPackage.project_id == project.id)).all()
        if (item.metadata_json or {}).get("source") == SOURCE_KEY
    ]
    if len(matches) > 1:
        raise ImportValidationError("Multiple RFQ packages match the Fernie project.")
    return matches[0] if matches else None


def _find_bid(db: Session, project: Project | None, tender: Tender | None) -> Bid | None:
    if project is None:
        return None
    matches = list(db.scalars(select(Bid).where(Bid.project_id == project.id)).all())
    sourced = [item for item in matches if (item.bid_json or {}).get("source") == SOURCE_KEY]
    if len(sourced) > 1:
        raise ImportValidationError("Multiple bid workspaces match the Fernie project.")
    if sourced:
        return sourced[0]
    if tender is not None:
        linked = [item for item in matches if item.tender_id == tender.id]
        if len(linked) == 1:
            return linked[0]
    return None


def _upsert_rfq_package(
    db: Session,
    project: Project,
    existing_tender: Tender | None,
    actor: str,
    timestamp: str,
) -> RFQPackage:
    rfq_package = _find_rfq_package(db, project, existing_tender)
    if rfq_package is None:
        rfq_package = RFQPackage(project_id=project.id, title=f"{FERNIE_TITLE} RFQ Package")
        db.add(rfq_package)
    rfq_package.project_name = project.name
    rfq_package.scope_summary = FERNIE_SCOPE
    rfq_package.due_at = FERNIE_CLOSING_AT
    rfq_package.status = "draft"
    rfq_package.supplier_category_targets = SUPPLIER_CATEGORIES
    rfq_package.metadata_json = {
        **(rfq_package.metadata_json or {}),
        "source": SOURCE_KEY,
        "historical_intake": True,
        "submission_status": "unverified",
        "audit_actor": actor,
        "imported_at": timestamp,
    }
    db.flush()
    return rfq_package


def _upsert_tender(
    db: Session,
    project: Project,
    rfq_package: RFQPackage,
    actor: str,
    timestamp: str,
) -> Tender:
    tender = _find_tender(db, project)
    if tender is None:
        tender = Tender(title=FERNIE_TITLE)
        db.add(tender)
    tender.project_id = project.id
    tender.rfq_package_id = rfq_package.id
    tender.title = FERNIE_TITLE
    tender.source = "City of Fernie RFP"
    tender.source_url = FERNIE_SOURCE_URL
    tender.owner = "City of Fernie"
    tender.municipality_name = "Fernie, BC"
    tender.closing_date = FERNIE_CLOSING_DATE
    tender.description = FERNIE_SCOPE
    tender.status = "reviewing"
    tender.estimated_value = FERNIE_VALUE
    tender.metadata_json = {
        **(tender.metadata_json or {}),
        "source": SOURCE_KEY,
        "historical_intake": True,
        "closing_passed": True,
        "submission_status": "unverified",
        "manhole_count": 11,
        "allowances": ALLOWANCES,
        "suggested_supplier_categories": SUPPLIER_CATEGORIES,
        "audit_actor": actor,
        "imported_at": timestamp,
    }
    db.flush()
    return tender


def _upsert_bid(
    db: Session,
    project: Project,
    tender: Tender,
    actor: str,
    timestamp: str,
) -> Bid:
    bid = _find_bid(db, project, tender)
    if bid is None:
        bid = Bid(project_id=project.id)
        db.add(bid)
    bid.tender_id = tender.id
    bid.status = "draft"
    bid.total_amount = FERNIE_VALUE
    bid.summary = (
        "Historical Fernie bid package. Closing passed; submission outcome is unverified. "
        "Do not treat as an active bid without owner confirmation."
    )
    bid.bid_json = {
        **(bid.bid_json or {}),
        "source": SOURCE_KEY,
        "historical_intake": True,
        "submission_status": "unverified",
        "scope": FERNIE_SCOPE,
        "manhole_count": 11,
        "allowances": ALLOWANCES,
        "estimate_drive_file_id": "1En-woddcXcOEySHB7F1Ps7hoqwm9ynnDIgnI7jwfVEc",
        "proposal_value_cad": 169500,
        "audit_actor": actor,
        "imported_at": timestamp,
    }
    db.flush()
    return bid


def _link_documents(
    db: Session,
    project: Project,
    tender: Tender,
    rfq_package: RFQPackage,
    folders: Sequence[TenderFolder],
) -> tuple[int, int]:
    source_ids = {
        drive_file.drive_file_id
        for folder in folders
        for drive_file in folder.files
    }
    documents = [
        document
        for document in db.scalars(select(Document).where(Document.project_id == project.id)).all()
        if (document.metadata_json or {}).get("drive_file_id") in source_ids
    ]
    existing_links = {
        (link.metadata_json or {}).get("source_document_id"): link
        for link in db.scalars(
            select(RFQPackageDocument).where(RFQPackageDocument.rfq_package_id == rfq_package.id)
        ).all()
    }
    for document in documents:
        document.tender_id = tender.id
        document.rfq_package_id = rfq_package.id
        key = str(document.id)
        link = existing_links.get(key)
        if link is None:
            link = RFQPackageDocument(
                rfq_package_id=rfq_package.id,
                document_type=document.category,
                title=document.title,
                required=True,
                status="attached",
                storage_uri=None,
                metadata_json={},
            )
            db.add(link)
        link.document_type = document.category
        link.title = document.title
        link.metadata_json = {
            **(link.metadata_json or {}),
            "source": SOURCE_KEY,
            "source_document_id": key,
            "drive_file_id": (document.metadata_json or {}).get("drive_file_id"),
            "drive_url": (document.metadata_json or {}).get("drive_url"),
            "source_immutable": True,
        }
    db.flush()
    return len(documents), len(existing_links) + sum(
        1 for document in documents if str(document.id) not in existing_links
    )


def _source_metadata(
    actor: str,
    timestamp: str,
    folders: Sequence[TenderFolder],
) -> dict[str, object]:
    return {
        "source_folder_ids": [folder.drive_folder_id for folder in folders],
        "source_folder_urls": [folder.url for folder in folders],
        "historical_intake": True,
        "closing_passed": True,
        "submission_status": "unverified",
        "audit_actor": actor,
        "imported_at": timestamp,
    }
