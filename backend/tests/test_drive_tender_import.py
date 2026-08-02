from app.services.drive_tender_import import TenderFolder, extract_reference, plan_import


def folder(folder_id: str, name: str) -> TenderFolder:
    return TenderFolder(
        drive_folder_id=folder_id,
        name=name,
        url=f"https://drive.google.com/drive/folders/{folder_id}",
    )


def test_extract_reference_handles_known_tender_formats() -> None:
    assert extract_reference("Village of Cumberland - ITT-2602") == "ITT-2602"
    assert extract_reference("Q26 335 - Firehall 3 Concrete Driveway") == "Q26-335"
    assert extract_reference("Hillcrest - 2311-30196-00") == "2311-30196-00"


def test_plan_import_consolidates_known_duplicate_names() -> None:
    decisions = plan_import(
        [
            folder("final-cumberland", "Village of Cumberland - 2026 Sewer Separation - ITT-2602"),
            folder("old-cumberland", "Cumberland sewer separation"),
            folder("final-fernie", "City of Fernie - 2026 Sanitary Manhole Infiltration Repair"),
            folder("old-fernie", "Sani manhole repair Fernie"),
            folder("parksville", "Parksville"),
        ]
    )

    consolidated = [decision for decision in decisions if decision.action == "consolidate"]
    assert len(consolidated) == 2
    assert {decision.source_folder_ids for decision in consolidated} == {
        ("final-cumberland", "old-cumberland"),
        ("final-fernie", "old-fernie"),
    }
    assert any(decision.canonical_name == "Parksville" for decision in decisions)


def test_plan_import_is_deterministic() -> None:
    folders = [folder("b", "Parksville"), folder("a", "Braidwood")]
    assert plan_import(folders) == plan_import(reversed(folders))
