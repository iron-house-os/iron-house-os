from datetime import datetime, timezone

import pytest
from app.models.document import Document
from app.models.project import Project
from app.services.drive_tender_import import (
    DriveFile,
    ImportValidationError,
    TenderFolder,
    extract_reference,
    import_drive_tenders,
    parse_manifest,
    plan_import,
)
from app.tools.drive_tender_import import require_staging_apply
from conftest import TestingSessionLocal
from sqlalchemy import func, select

IMPORTED_AT = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


def drive_file(file_id: str, name: str) -> DriveFile:
    return DriveFile(
        drive_file_id=file_id,
        name=name,
        mime_type="application/pdf",
        url=f"https://drive.google.com/file/d/{file_id}/view",
        created_time="2026-08-01T00:00:00Z",
        modified_time="2026-08-02T00:00:00Z",
    )


def folder(folder_id: str, name: str, *files: DriveFile) -> TenderFolder:
    return TenderFolder(
        drive_folder_id=folder_id,
        name=name,
        url=f"https://drive.google.com/drive/folders/{folder_id}",
        files=tuple(files),
    )


def tender_folders() -> tuple[TenderFolder, ...]:
    return (
        folder(
            "folder-cumberland-full",
            "Village of Cumberland - 2026 Sewer Separation - ITT-2602",
            drive_file("file-cumberland-001", "ITT-2602 Tender.pdf"),
        ),
        folder("folder-cumberland-old", "Cumberland sewer separation"),
        folder(
            "folder-hillcrest-main",
            "Hillcrest Avenue Storm Rehabilitation - 2311-30196-00",
            drive_file("file-hillcrest-001", "District of Port Edward Hillcrest Tender.pdf"),
            drive_file("file-hillcrest-002", "10482-C Series IFT.pdf"),
        ),
        folder(
            "folder-edward-alias",
            "Edward sewer",
            drive_file("file-edward-copy-01", "District of Port Edward Hillcrest Tender.pdf"),
            drive_file("file-edward-copy-02", "10482-C Series IFT.pdf"),
        ),
        folder("folder-we-fireball", "We fireball"),
        folder(
            "folder-q26-firehall",
            "Q26 335 - Firehall 3 Concrete Driveway",
            drive_file("file-firehall-0001", "Q26_335_Firehall_3_Concrete_Driveway.pdf"),
        ),
    )


def test_extract_reference_handles_approved_source_formats() -> None:
    assert extract_reference("Village of Cumberland - ITT-2602") == "ITT-2602"
    assert extract_reference("Q26 335 - Firehall 3 Concrete Driveway") == "Q26-335"
    assert extract_reference("Hillcrest - 2311-30196-00") == "2311-30196-00"
    assert extract_reference("RFP_2026-003 Construction Services") == "RFP-2026-003"
    assert extract_reference("C26-085 Braidwood") == "C26-085"


def test_plan_consolidates_verified_aliases_and_flags_unverified_empty_alias() -> None:
    decisions = plan_import(tender_folders())

    consolidated = [item for item in decisions if item.action == "consolidate"]
    assert {item.source_folder_ids for item in consolidated} == {
        ("folder-cumberland-full", "folder-cumberland-old"),
        ("folder-edward-alias", "folder-hillcrest-main"),
    }
    ambiguous = next(item for item in decisions if item.action == "ambiguous")
    assert ambiguous.source_folder_ids == ("folder-we-fireball",)
    firehall = next(item for item in decisions if item.reference == "Q26-335")
    assert firehall.source_folder_ids == ("folder-q26-firehall",)


def test_manifest_validation_rejects_duplicate_stable_file_ids() -> None:
    payload = {
        "source": "google_drive",
        "folders": [
            {
                "drive_folder_id": "folder-0000000001",
                "name": "Tender A",
                "url": "https://drive.google.com/drive/folders/folder-0000000001",
                "files": [
                    {
                        "drive_file_id": "file-00000000001",
                        "name": "A.pdf",
                        "mime_type": "application/pdf",
                        "url": "https://drive.google.com/file/d/file-00000000001/view",
                    }
                ],
            },
            {
                "drive_folder_id": "folder-0000000002",
                "name": "Tender B",
                "url": "https://drive.google.com/drive/folders/folder-0000000002",
                "files": [
                    {
                        "drive_file_id": "file-00000000001",
                        "name": "B.pdf",
                        "mime_type": "application/pdf",
                        "url": "https://drive.google.com/file/d/file-00000000001/view",
                    }
                ],
            },
        ],
    }

    with pytest.raises(ImportValidationError, match="Duplicate Drive file ID"):
        parse_manifest(payload)


def test_dry_run_reports_without_mutating_database() -> None:
    with TestingSessionLocal() as db:
        report = import_drive_tenders(
            db,
            [tender_folders()[0]],
            actor="Staging Operator",
            imported_at=IMPORTED_AT,
        )

        assert report["status"] == "dry_run"
        assert report["summary"]["create"] == 1
        assert db.scalar(select(func.count()).select_from(Project)) == 0
        assert db.scalar(select(func.count()).select_from(Document)) == 0


def test_apply_is_idempotent_and_preserves_external_source_metadata() -> None:
    source = [tender_folders()[0]]
    with TestingSessionLocal() as db:
        first = import_drive_tenders(
            db,
            source,
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()
        second = import_drive_tenders(
            db,
            source,
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()

        project = db.scalar(select(Project))
        document = db.scalar(select(Document))
        assert first["summary"]["create"] == 1
        assert second["summary"]["update"] == 1
        assert db.scalar(select(func.count()).select_from(Project)) == 1
        assert db.scalar(select(func.count()).select_from(Document)) == 1
        assert project.status == "tendering"
        assert project.tender_number == "ITT-2602"
        assert project.client_owner == "Village of Cumberland"
        assert document.project_id == project.id
        assert document.storage_uri is None
        assert document.metadata_json["drive_file_id"] == "file-cumberland-001"
        assert document.metadata_json["drive_url"].startswith("https://drive.google.com/")
        assert document.metadata_json["source_immutable"] is True


def test_existing_project_is_updated_instead_of_duplicated() -> None:
    with TestingSessionLocal() as db:
        existing = Project(
            name="Village of Cumberland - 2026 Sewer Separation - ITT-2602",
            tender_number="ITT-2602",
            status="tendering",
            metadata_json={"kept": True},
        )
        db.add(existing)
        db.commit()

        report = import_drive_tenders(
            db,
            [tender_folders()[0]],
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()

        assert report["summary"]["update"] == 1
        assert db.scalar(select(func.count()).select_from(Project)) == 1
        db.refresh(existing)
        assert existing.metadata_json["kept"] is True
        assert existing.metadata_json["drive_tender_import"]["audit_actor"] == "Staging Operator"


def test_file_link_is_not_moved_between_projects() -> None:
    source = tender_folders()[0]
    with TestingSessionLocal() as db:
        other_project = Project(name="Other project", status="tendering", metadata_json={})
        db.add(other_project)
        db.flush()
        db.add(
            Document(
                title="Existing source",
                category="other",
                status="registered",
                project_id=other_project.id,
                metadata_json={"drive_file_id": "file-cumberland-001"},
            )
        )
        db.commit()

        report = import_drive_tenders(
            db,
            [source],
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )

        assert report["unresolved"][0]["reason"] == "Drive file ID is already linked outside the matched project"
        assert db.scalar(select(func.count()).select_from(Document)) == 1


def test_apply_is_locked_to_staging() -> None:
    require_staging_apply("staging", True)
    require_staging_apply("development", False)
    with pytest.raises(ImportValidationError, match="locked to an IHOS staging"):
        require_staging_apply("production", True)
