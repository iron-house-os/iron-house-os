"""Controlled staging intake for issue #134 fuel-standard estimate revisions.

Only the two estimates that were active on the 2026-08-19 source review are
included. The Drive source files remain immutable. Replacement estimates are
provisional until an estimator confirms the duration and equipment-hour basis.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.bid import Bid
from app.models.document import Document
from app.models.project import Project
from app.models.tender import Tender
from app.services.drive_tender_import import ImportValidationError, normalize_tender_name
from sqlalchemy import select
from sqlalchemy.orm import Session

SOURCE_KEY = "fuel_estimate_rebuild_issue_134"
REBUILD_DATE = date(2026, 8, 19)
FUEL_RATE_CAD_PER_LITRE = Decimal("2.50")
PREVIOUS_FUEL_RATE_CAD_PER_LITRE = Decimal("2.00")


@dataclass(frozen=True)
class EstimateRevision:
    key: str
    project_name: str
    tender_number: str
    owner: str
    municipality: str
    closing_date: date
    source_folder_id: str
    source_file_id: str
    source_title: str
    replacement_file_id: str
    replacement_title: str
    old_total: Decimal
    new_total: Decimal
    fuel_litres: Decimal
    old_fuel_cost: Decimal
    new_fuel_cost: Decimal
    direct_fuel_variance: Decimal
    tender_variance: Decimal

    @property
    def source_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.source_file_id}/edit"

    @property
    def replacement_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.replacement_file_id}/edit"


ESTIMATE_REVISIONS = (
    EstimateRevision(
        key="braidwood_c26_085",
        project_name="Braidwood Road Corridor Improvements",
        tender_number="C26-085",
        owner="City of Courtenay",
        municipality="Courtenay, BC",
        closing_date=date(2026, 8, 20),
        source_folder_id="1E9HmYXU39jghxu0xNorCqsEegV7cui3N",
        source_file_id="1zC0CKUizVFKEGutIKGv3mW-PyZspzlVz",
        source_title="IH-Estimate-BraidwoodRoad-C26-085-2026-07-27-v1.xlsx",
        replacement_file_id="18KxEAuCM87Cpph7yUq0prJ55FdWcfqSw",
        replacement_title="IH-Estimate-BraidwoodRoad-C26-085-2026-08-19-fuel-v2.xlsx",
        old_total=Decimal("13212251.87"),
        new_total=Decimal("13234351.13"),
        fuel_litres=Decimal("33825.0"),
        old_fuel_cost=Decimal("67650.00"),
        new_fuel_cost=Decimal("84562.50"),
        direct_fuel_variance=Decimal("16912.50"),
        tender_variance=Decimal("22099.26"),
    ),
    EstimateRevision(
        key="cumberland_itt_2602",
        project_name="Village of Cumberland - 2026 Sewer Separation Package",
        tender_number="ITT-2602",
        owner="Village of Cumberland",
        municipality="Cumberland, BC",
        closing_date=date(2026, 8, 20),
        source_folder_id="15tpur5YZr-UzF7I_zlNemhTGEWhOwsyg",
        source_file_id="1d6sRDMNPmHI6Cwaup6Zrlv4OuaD0oMhvqKEqXeRuF8Q",
        source_title="ITT-2602 Cumberland Sewer Separation - Estimate",
        replacement_file_id="115TFp1JR8yOLPkFOOWtem12xGcuXvHoSXIF9EjFR0KY",
        replacement_title="ITT-2602 Cumberland Sewer Separation - Estimate - Fuel v2 - 2026-08-19",
        old_total=Decimal("5123740.00"),
        new_total=Decimal("5130802.50"),
        fuel_litres=Decimal("14125.0"),
        old_fuel_cost=Decimal("28250.00"),
        new_fuel_cost=Decimal("35312.50"),
        direct_fuel_variance=Decimal("7062.50"),
        tender_variance=Decimal("7062.50"),
    ),
)


def expired_revision_keys(as_of: date) -> list[str]:
    return sorted(item.key for item in ESTIMATE_REVISIONS if item.closing_date < as_of)


def import_fuel_estimate_revisions(
    db: Session,
    *,
    actor: str,
    apply: bool = False,
    imported_at: datetime | None = None,
) -> dict[str, object]:
    """Plan or atomically apply the two controlled estimate revisions.

    The caller owns commit/rollback. No Drive file content is downloaded or
    changed; IHOS stores links, revision state, totals, and audit metadata only.
    """
    actor = actor.strip()
    if not actor:
        raise ImportValidationError("An audit actor is required.")
    now = (imported_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    timestamp = now.isoformat()
    records: list[dict[str, object]] = []

    for revision in ESTIMATE_REVISIONS:
        project = _find_project(db, revision)
        tender = _find_tender(db, project, revision)
        bid = _find_bid(db, project, tender, revision)
        source_document = _find_document(db, project, revision.source_file_id)
        replacement_document = _find_document(db, project, revision.replacement_file_id)
        closing_passed = revision.closing_date < now.date()
        actions = {
            "project": "update" if project else "create",
            "tender": "update" if tender else "create",
            "bid_workspace": "update" if bid else "create",
            "source_estimate": "archive" if source_document else "register_archived",
            "replacement_estimate": "update" if replacement_document else "register",
        }
        record: dict[str, object] = {
            "key": revision.key,
            "project": revision.project_name,
            "tender_number": revision.tender_number,
            "classification": "active_at_rebuild",
            "classification_date": REBUILD_DATE.isoformat(),
            "closing_date": revision.closing_date.isoformat(),
            "closing_passed_at_import": closing_passed,
            "provisional": True,
            "submission_ready": False,
            "source_file_id": revision.source_file_id,
            "replacement_file_id": revision.replacement_file_id,
            "old_total_cad": float(revision.old_total),
            "new_total_cad": float(revision.new_total),
            "fuel_litres": float(revision.fuel_litres),
            "fuel_cost_cad": float(revision.new_fuel_cost),
            "direct_fuel_variance_cad": float(revision.direct_fuel_variance),
            "tender_variance_cad": float(revision.tender_variance),
            "actions": actions,
        }
        if not apply:
            records.append(record)
            continue

        project = _upsert_project(db, project, revision, actor, timestamp, closing_passed)
        tender = _upsert_tender(db, project, tender, revision, actor, timestamp, closing_passed)
        bid = _upsert_bid(db, project, tender, bid, revision, actor, timestamp, closing_passed)
        source_document = _upsert_document(
            db,
            project,
            tender,
            source_document,
            revision,
            baseline=True,
            actor=actor,
            timestamp=timestamp,
        )
        replacement_document = _upsert_document(
            db,
            project,
            tender,
            replacement_document,
            revision,
            baseline=False,
            actor=actor,
            timestamp=timestamp,
        )
        db.flush()
        record.update(
            {
                "project_id": str(project.id),
                "tender_id": str(tender.id),
                "bid_id": str(bid.id),
                "source_document_id": str(source_document.id),
                "replacement_document_id": str(replacement_document.id),
                "source_document_status": source_document.status,
                "replacement_document_status": replacement_document.status,
            }
        )
        records.append(record)

    return {
        "status": "applied" if apply else "dry_run",
        "source": SOURCE_KEY,
        "actor": actor,
        "imported_at": timestamp,
        "staging_only": True,
        "fuel_rate_cad_per_litre": float(FUEL_RATE_CAD_PER_LITRE),
        "provisional": True,
        "submission_ready": False,
        "expired_revision_keys": expired_revision_keys(now.date()),
        "records": records,
    }


def _find_project(db: Session, revision: EstimateRevision) -> Project | None:
    matches: list[Project] = []
    target_name = normalize_tender_name(revision.project_name)
    for project in db.scalars(select(Project)).all():
        metadata = project.metadata_json or {}
        source = metadata.get(SOURCE_KEY, {}) if isinstance(metadata, Mapping) else {}
        records = source.get("records", {}) if isinstance(source, Mapping) else {}
        if (
            project.tender_number == revision.tender_number
            or normalize_tender_name(project.name) == target_name
            or (isinstance(records, Mapping) and revision.key in records)
        ):
            matches.append(project)
    if len(matches) > 1:
        raise ImportValidationError(f"Multiple IHOS projects match {revision.tender_number}.")
    return matches[0] if matches else None


def _find_tender(
    db: Session,
    project: Project | None,
    revision: EstimateRevision,
) -> Tender | None:
    matches = [
        tender
        for tender in db.scalars(select(Tender)).all()
        if tender.tender_number == revision.tender_number
        or (project is not None and tender.project_id == project.id)
    ]
    unique = list({item.id: item for item in matches}.values())
    if len(unique) > 1:
        raise ImportValidationError(f"Multiple IHOS tenders match {revision.tender_number}.")
    return unique[0] if unique else None


def _find_bid(
    db: Session,
    project: Project | None,
    tender: Tender | None,
    revision: EstimateRevision,
) -> Bid | None:
    if project is None:
        return None
    bids = list(db.scalars(select(Bid).where(Bid.project_id == project.id)).all())
    sourced = [
        bid
        for bid in bids
        if (bid.bid_json or {}).get("source") == SOURCE_KEY
        and (bid.bid_json or {}).get("revision_key") == revision.key
    ]
    if len(sourced) > 1:
        raise ImportValidationError(f"Multiple fuel-revision bids match {revision.tender_number}.")
    if sourced:
        return sourced[0]
    reusable = [
        bid
        for bid in bids
        if bid.submitted_at is None and (tender is None or bid.tender_id in (None, tender.id))
    ]
    if len(reusable) > 1:
        raise ImportValidationError(f"Multiple draft bids match {revision.tender_number}.")
    return reusable[0] if reusable else None


def _find_document(
    db: Session,
    project: Project | None,
    drive_file_id: str,
) -> Document | None:
    matches = [
        document
        for document in db.scalars(select(Document)).all()
        if (document.metadata_json or {}).get("drive_file_id") == drive_file_id
    ]
    if len(matches) > 1:
        raise ImportValidationError(f"Drive file {drive_file_id} is linked more than once.")
    if matches and project is not None and matches[0].project_id not in (None, project.id):
        raise ImportValidationError(f"Drive file {drive_file_id} is linked to another project.")
    return matches[0] if matches else None


def _upsert_project(
    db: Session,
    project: Project | None,
    revision: EstimateRevision,
    actor: str,
    timestamp: str,
    closing_passed: bool,
) -> Project:
    if project is None:
        project = Project(name=revision.project_name)
        db.add(project)
    project.name = revision.project_name
    project.client_owner = revision.owner
    project.municipality_name = revision.municipality
    project.tender_number = revision.tender_number
    project.tender_source = "Google Drive / issue #134"
    project.tender_closing_date = revision.closing_date
    project.bid_due_date = revision.closing_date
    project.contract_value = revision.new_total
    project.status = "opportunity" if closing_passed else "tendering"
    project.metadata_json = _merge_source_metadata(
        project.metadata_json,
        revision,
        actor,
        timestamp,
        closing_passed,
    )
    db.flush()
    return project


def _upsert_tender(
    db: Session,
    project: Project,
    tender: Tender | None,
    revision: EstimateRevision,
    actor: str,
    timestamp: str,
    closing_passed: bool,
) -> Tender:
    if tender is None:
        tender = Tender(title=revision.project_name)
        db.add(tender)
    tender.project_id = project.id
    tender.title = revision.project_name
    tender.tender_number = revision.tender_number
    tender.source = "Google Drive / issue #134"
    tender.source_url = f"https://drive.google.com/drive/folders/{revision.source_folder_id}"
    tender.owner = revision.owner
    tender.municipality_name = revision.municipality
    tender.closing_date = revision.closing_date
    tender.status = "reviewing"
    tender.estimated_value = revision.new_total
    tender.metadata_json = _merge_source_metadata(
        tender.metadata_json,
        revision,
        actor,
        timestamp,
        closing_passed,
    )
    db.flush()
    return tender


def _upsert_bid(
    db: Session,
    project: Project,
    tender: Tender,
    bid: Bid | None,
    revision: EstimateRevision,
    actor: str,
    timestamp: str,
    closing_passed: bool,
) -> Bid:
    if bid is None:
        bid = Bid(project_id=project.id)
        db.add(bid)
    bid.tender_id = tender.id
    bid.status = "draft"
    bid.total_amount = revision.new_total
    bid.summary = (
        "Provisional CAD 2.50/L fuel-standard estimate. Estimator confirmation is required "
        "before submission; Drive baseline remains immutable."
    )
    bid.bid_json = {
        **(bid.bid_json or {}),
        "source": SOURCE_KEY,
        "revision_key": revision.key,
        "classification": "active_at_rebuild",
        "classification_date": REBUILD_DATE.isoformat(),
        "closing_passed_at_import": closing_passed,
        "submission_status": "unverified" if closing_passed else "not_submitted",
        "provisional": True,
        "submission_ready": False,
        "source_estimate_drive_file_id": revision.source_file_id,
        "replacement_estimate_drive_file_id": revision.replacement_file_id,
        "old_total_cad": float(revision.old_total),
        "new_total_cad": float(revision.new_total),
        "fuel_litres": float(revision.fuel_litres),
        "fuel_rate_cad_per_litre": float(FUEL_RATE_CAD_PER_LITRE),
        "fuel_cost_cad": float(revision.new_fuel_cost),
        "direct_fuel_variance_cad": float(revision.direct_fuel_variance),
        "tender_variance_cad": float(revision.tender_variance),
        "audit_actor": actor,
        "imported_at": timestamp,
    }
    db.flush()
    return bid


def _upsert_document(
    db: Session,
    project: Project,
    tender: Tender,
    document: Document | None,
    revision: EstimateRevision,
    *,
    baseline: bool,
    actor: str,
    timestamp: str,
) -> Document:
    drive_file_id = revision.source_file_id if baseline else revision.replacement_file_id
    title = revision.source_title if baseline else revision.replacement_title
    drive_url = revision.source_url if baseline else revision.replacement_url
    if document is None:
        document = Document(title=title, category="other")
        db.add(document)
    document.title = title
    document.category = "other"
    document.status = "archived" if baseline else "registered"
    document.project_id = project.id
    document.tender_id = tender.id
    document.revision = "baseline-superseded" if baseline else "fuel-v2-2026-08-19"
    document.issue_date = REBUILD_DATE if not baseline else document.issue_date
    document.storage_uri = None
    document.description = (
        "Immutable Drive baseline superseded by the issue #134 fuel-standard revision."
        if baseline
        else "Provisional CAD 2.50/L fuel-standard replacement; estimator confirmation required."
    )
    metadata = dict(document.metadata_json or {})
    metadata.update(
        {
            "external_provider": "google_drive",
            "drive_file_id": drive_file_id,
            "drive_url": drive_url,
            "original_filename": title,
            "source_folder_ids": [revision.source_folder_id],
            "source": SOURCE_KEY,
            "document_role": "estimate",
            "revision_key": revision.key,
            "record_status": "superseded_archived" if baseline else "provisional_active",
            "source_immutable": True,
            "provisional": not baseline,
            "submission_ready": False,
            "audit_actor": actor,
            "imported_at": timestamp,
        }
    )
    if baseline:
        metadata["superseded_by_drive_file_id"] = revision.replacement_file_id
    else:
        metadata.update(
            {
                "supersedes_drive_file_id": revision.source_file_id,
                "old_total_cad": float(revision.old_total),
                "new_total_cad": float(revision.new_total),
                "fuel_litres": float(revision.fuel_litres),
                "fuel_rate_cad_per_litre": float(FUEL_RATE_CAD_PER_LITRE),
                "fuel_cost_cad": float(revision.new_fuel_cost),
                "direct_fuel_variance_cad": float(revision.direct_fuel_variance),
                "tender_variance_cad": float(revision.tender_variance),
            }
        )
    document.metadata_json = metadata
    db.flush()
    return document


def _merge_source_metadata(
    existing: Mapping[str, object] | None,
    revision: EstimateRevision,
    actor: str,
    timestamp: str,
    closing_passed: bool,
) -> dict[str, object]:
    metadata = dict(existing or {})
    source = metadata.get(SOURCE_KEY, {})
    source_data = dict(source) if isinstance(source, Mapping) else {}
    records = source_data.get("records", {})
    record_data = dict(records) if isinstance(records, Mapping) else {}
    record_data[revision.key] = {
        "classification": "active_at_rebuild",
        "classification_date": REBUILD_DATE.isoformat(),
        "closing_passed_at_import": closing_passed,
        "submission_status": "unverified" if closing_passed else "not_submitted",
        "source_folder_id": revision.source_folder_id,
        "source_file_id": revision.source_file_id,
        "replacement_file_id": revision.replacement_file_id,
        "old_total_cad": float(revision.old_total),
        "new_total_cad": float(revision.new_total),
        "fuel_litres": float(revision.fuel_litres),
        "fuel_rate_cad_per_litre": float(FUEL_RATE_CAD_PER_LITRE),
        "fuel_cost_cad": float(revision.new_fuel_cost),
        "direct_fuel_variance_cad": float(revision.direct_fuel_variance),
        "tender_variance_cad": float(revision.tender_variance),
        "provisional": True,
        "submission_ready": False,
        "audit_actor": actor,
        "imported_at": timestamp,
    }
    source_data["records"] = record_data
    metadata[SOURCE_KEY] = source_data
    return metadata
