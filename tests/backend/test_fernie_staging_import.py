from datetime import datetime, timezone

import pytest
from app.models.bid import Bid
from app.models.document import Document
from app.models.project import Project
from app.models.rfq import RFQPackage, RFQPackageDocument
from app.models.tender import Tender
from app.services.drive_tender_import import DriveFile, ImportValidationError, TenderFolder
from app.services.fernie_staging_import import import_fernie_bid_package
from app.tools.fernie_staging_import import require_expired_intake_confirmation
from conftest import TestingSessionLocal
from sqlalchemy import func, select

IMPORTED_AT = datetime(2026, 8, 19, 0, 0, tzinfo=timezone.utc)


def source_folders() -> tuple[TenderFolder, ...]:
    return (
        TenderFolder(
            drive_folder_id="1x8jdyiBthezgTOHUrluRJXy8AHff9vaT",
            name="City of Fernie - 2026 Sanitary Manhole Infiltration Repair",
            url="https://drive.google.com/drive/folders/1x8jdyiBthezgTOHUrluRJXy8AHff9vaT",
            files=(
                drive_file(
                    "1En-woddcXcOEySHB7F1Ps7hoqwm9ynnDIgnI7jwfVEc",
                    "City of Fernie - 2026 Manhole Infiltration Repair - Estimate",
                    "application/vnd.google-apps.spreadsheet",
                ),
                drive_file(
                    "1bKp0GweJp4fSpFPCL3qfguJRqOvxWjUoi9XJLNqpt5w",
                    "City of Fernie - 2026 Manhole Infiltration Repair - Proposal",
                    "application/vnd.google-apps.document",
                ),
                drive_file(
                    "1OVQvFtntl_XhcLGjRJanMJXeNGgAJyHY",
                    "City of Fernie - 2026 Manhole Infiltration Repair - Proposal.pdf",
                    "application/pdf",
                ),
            ),
        ),
        TenderFolder(
            drive_folder_id="1dA9BCow-rTCqivIR0lZ-GcS4lTciN8MT",
            name="Sani manhole repair Fernie",
            url="https://drive.google.com/drive/folders/1dA9BCow-rTCqivIR0lZ-GcS4lTciN8MT",
            files=(
                drive_file(
                    "1L6SBz65W8PfC_2Aq5PWRa8T_Pi1WSRcK",
                    "2026_Manhole_Infiltration_Repair_Program_RFP.pdf",
                    "application/pdf",
                ),
            ),
        ),
    )


def drive_file(file_id: str, name: str, mime_type: str) -> DriveFile:
    return DriveFile(
        drive_file_id=file_id,
        name=name,
        mime_type=mime_type,
        url=f"https://drive.google.com/file/d/{file_id}/view",
    )


def test_dry_run_reports_historical_status_without_database_mutation() -> None:
    with TestingSessionLocal() as db:
        report = import_fernie_bid_package(
            db,
            source_folders(),
            actor="Staging Operator",
            imported_at=IMPORTED_AT,
        )

        assert report["status"] == "dry_run"
        assert report["historical_intake"] is True
        assert report["closing_passed"] is True
        assert report["submission_status"] == "unverified"
        assert report["objects"] == {
            "project": "create",
            "tender": "create",
            "rfq_package": "create",
            "bid_workspace": "create",
        }
        assert db.scalar(select(func.count()).select_from(Project)) == 0
        assert db.scalar(select(func.count()).select_from(Tender)) == 0


def test_apply_is_idempotent_and_links_all_controlled_objects() -> None:
    with TestingSessionLocal() as db:
        first = import_fernie_bid_package(
            db,
            source_folders(),
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()
        second = import_fernie_bid_package(
            db,
            source_folders(),
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()

        assert first["linked_document_count"] == 4
        assert second["objects"] == {
            "project": "update",
            "tender": "update",
            "rfq_package": "update",
            "bid_workspace": "update",
        }
        assert db.scalar(select(func.count()).select_from(Project)) == 1
        assert db.scalar(select(func.count()).select_from(Tender)) == 1
        assert db.scalar(select(func.count()).select_from(RFQPackage)) == 1
        assert db.scalar(select(func.count()).select_from(Bid)) == 1
        assert db.scalar(select(func.count()).select_from(Document)) == 4
        assert db.scalar(select(func.count()).select_from(RFQPackageDocument)) == 4

        project = db.scalar(select(Project))
        tender = db.scalar(select(Tender))
        bid = db.scalar(select(Bid))
        documents = list(db.scalars(select(Document)).all())
        rfq_documents = list(db.scalars(select(RFQPackageDocument)).all())
        assert project.status == "opportunity"
        assert project.contract_value == 169500
        assert tender.status == "reviewing"
        assert tender.metadata_json["submission_status"] == "unverified"
        assert tender.metadata_json["manhole_count"] == 11
        assert bid.status == "draft"
        assert bid.total_amount == 169500
        assert all(document.tender_id == tender.id for document in documents)
        assert all(document.rfq_package_id is not None for document in documents)
        assert all(document.status == "attached" for document in rfq_documents)


def test_rfq_document_default_matches_database_constraint() -> None:
    assert RFQPackageDocument.__table__.c.status.default.arg == "pending"


def test_apply_requires_expired_intake_confirmation() -> None:
    require_expired_intake_confirmation(False, False)
    require_expired_intake_confirmation(True, True)
    with pytest.raises(ImportValidationError, match="confirm-expired-intake"):
        require_expired_intake_confirmation(True, False)


def test_manifest_must_contain_both_fernie_source_folders() -> None:
    with TestingSessionLocal() as db, pytest.raises(
        ImportValidationError,
        match="missing source folders",
    ):
        import_fernie_bid_package(
            db,
            source_folders()[:1],
            actor="Staging Operator",
        )
