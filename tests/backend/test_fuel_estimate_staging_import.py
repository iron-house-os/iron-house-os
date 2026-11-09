from datetime import date, datetime, timezone

import pytest
from app.models.bid import Bid
from app.models.document import Document
from app.models.project import Project
from app.models.tender import Tender
from app.services.drive_tender_import import ImportValidationError
from app.services.fuel_estimate_staging_import import import_fuel_estimate_revisions
from app.tools.fuel_estimate_staging_import import (
    require_expired_intake_confirmation,
    require_provisional_confirmation,
)
from conftest import TestingSessionLocal
from sqlalchemy import func, select

IMPORTED_AT = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def test_dry_run_reports_both_provisional_revisions_without_mutation() -> None:
    with TestingSessionLocal() as db:
        report = import_fuel_estimate_revisions(
            db,
            actor="Staging Operator",
            imported_at=IMPORTED_AT,
        )

        assert report["status"] == "dry_run"
        assert report["staging_only"] is True
        assert report["fuel_rate_cad_per_litre"] == 2.5
        assert report["provisional"] is True
        assert report["submission_ready"] is False
        assert len(report["records"]) == 2
        assert {item["tender_number"] for item in report["records"]} == {"C26-085", "ITT-2602"}
        assert all(item["classification"] == "active_at_rebuild" for item in report["records"])
        assert all(item["submission_ready"] is False for item in report["records"])
        assert db.scalar(select(func.count()).select_from(Project)) == 0
        assert db.scalar(select(func.count()).select_from(Document)) == 0


def test_apply_is_idempotent_and_archives_only_the_ihos_baseline_link() -> None:
    with TestingSessionLocal() as db:
        first = import_fuel_estimate_revisions(
            db,
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()
        second = import_fuel_estimate_revisions(
            db,
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()

        assert first["status"] == "applied"
        assert all(item["source_document_status"] == "archived" for item in first["records"])
        assert all(item["replacement_document_status"] == "registered" for item in first["records"])
        assert all(item["actions"]["project"] == "update" for item in second["records"])
        assert all(
            item["actions"]["replacement_estimate"] == "update" for item in second["records"]
        )
        assert db.scalar(select(func.count()).select_from(Project)) == 2
        assert db.scalar(select(func.count()).select_from(Tender)) == 2
        assert db.scalar(select(func.count()).select_from(Bid)) == 2
        assert db.scalar(select(func.count()).select_from(Document)) == 4

        documents = list(db.scalars(select(Document)).all())
        baseline = [item for item in documents if item.status == "archived"]
        replacements = [item for item in documents if item.status == "registered"]
        assert len(baseline) == 2
        assert len(replacements) == 2
        assert all(item.category == "other" for item in documents)
        assert all(item.metadata_json["document_role"] == "estimate" for item in documents)
        assert all(
            item.metadata_json["record_status"] == "superseded_archived" for item in baseline
        )
        assert all(item.metadata_json["source_immutable"] is True for item in baseline)
        assert all(item.metadata_json["provisional"] is True for item in replacements)
        assert all(item.metadata_json["submission_ready"] is False for item in replacements)

        totals = {
            item.tender.tender_number: float(item.total_amount)
            for item in db.scalars(select(Bid)).all()
        }
        assert totals == {"C26-085": 13234351.13, "ITT-2602": 5130802.5}


def test_existing_drive_import_records_are_reused_without_duplicates() -> None:
    with TestingSessionLocal() as db:
        project = Project(
            name="Village of Cumberland - 2026 Sewer Separation - ITT-2602",
            tender_number="ITT-2602",
            status="tendering",
            metadata_json={
                "drive_tender_import": {
                    "source_folder_ids": ["15tpur5YZr-UzF7I_zlNemhTGEWhOwsyg"]
                }
            },
        )
        db.add(project)
        db.flush()
        db.add(
            Document(
                title="ITT-2602 Cumberland Sewer Separation - Estimate",
                category="other",
                project_id=project.id,
                metadata_json={
                    "drive_file_id": "1d6sRDMNPmHI6Cwaup6Zrlv4OuaD0oMhvqKEqXeRuF8Q"
                },
            )
        )
        db.commit()

        report = import_fuel_estimate_revisions(
            db,
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()

        cumberland = next(item for item in report["records"] if item["tender_number"] == "ITT-2602")
        assert cumberland["actions"]["project"] == "update"
        assert cumberland["actions"]["source_estimate"] == "archive"
        assert db.scalar(select(func.count()).select_from(Project)) == 2
        assert db.scalar(select(func.count()).select_from(Document)) == 4


def test_apply_requires_provisional_and_expired_acknowledgements() -> None:
    require_provisional_confirmation(False, False)
    require_provisional_confirmation(True, True)
    with pytest.raises(ImportValidationError, match="confirm-provisional-estimates"):
        require_provisional_confirmation(True, False)

    require_expired_intake_confirmation(False, False, date(2026, 8, 21))
    require_expired_intake_confirmation(True, True, date(2026, 8, 21))
    require_expired_intake_confirmation(True, False, date(2026, 8, 19))
    with pytest.raises(ImportValidationError, match="confirm-expired-intake"):
        require_expired_intake_confirmation(True, False, date(2026, 8, 21))


def test_actor_is_required() -> None:
    with TestingSessionLocal() as db, pytest.raises(ImportValidationError, match="audit actor"):
        import_fuel_estimate_revisions(db, actor=" ")
