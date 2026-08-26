from datetime import date

from app.schemas.project_folder import ProjectFolderRequest
from app.services.project_folders import (
    build_awarded_project_folder_manifest,
    build_project_folder_manifest,
    build_root_folder_name,
)


def test_build_root_folder_name_strips_special_characters() -> None:
    root = build_root_folder_name(
        close_date=date(2026, 7, 15),
        owner="City of Surrey",
        project_code="WR26-012",
        project_name="Marine Drive Parking Lot",
    )

    assert root == "2026-07-15_CityofSurrey_WR26012_MarineDriveParkingLot"


def test_build_project_folder_manifest_includes_required_entries() -> None:
    payload = ProjectFolderRequest(
        project_name="Marine Drive Parking Lot",
        owner="City of Surrey",
        project_code="WR26-012",
        close_date=date(2026, 7, 15),
        consultant="Example Consultant",
        estimator="Iron House",
    )

    manifest = build_project_folder_manifest(payload)
    paths = {entry.path for entry in manifest.entries}

    assert manifest.root_folder == "2026-07-15_CityofSurrey_WR26012_MarineDriveParkingLot"
    assert f"{manifest.root_folder}/02_Drawings/Current" in paths
    assert f"{manifest.root_folder}/07_RFQs/Asphalt" in paths
    assert f"{manifest.root_folder}/11_Submission" in paths
    assert f"{manifest.root_folder}/PROJECT_INDEX.md" in paths
    assert "Project: Marine Drive Parking Lot" in manifest.project_index
    assert "Owner / Municipality: City of Surrey" in manifest.project_index


def test_build_awarded_project_folder_manifest_uses_permanent_job_number() -> None:
    manifest = build_awarded_project_folder_manifest(
        job_number="IH-2026-014",
        project_name="Awarded Culvert Replacement",
        client_owner="District of Example",
        municipality="Example",
        tender_number="ITT-2026-14",
        tender_closing_date=date(2026, 8, 15),
    )

    assert manifest.root_folder == "IH-2026-014_AwardedCulvertReplacement"
    assert f"{manifest.root_folder}/13_Award_Handoff" in {entry.path for entry in manifest.entries}
    assert "Job Number: IH-2026-014" in manifest.project_index
    assert "Project Status: Awarded" in manifest.project_index
