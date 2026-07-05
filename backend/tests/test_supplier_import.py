from app.schemas.supplier_import import SupplierImportPreviewRequest, SupplierImportRow
from app.services.supplier_import import normalize_category, normalize_import_row, normalize_status, preview_supplier_import


def test_normalize_category_maps_common_aliases() -> None:
    assert normalize_category("pipe") == "Pipe / Utilities"
    assert normalize_category("catch basin") == "Manholes / Catch Basins"
    assert normalize_category("geo") == "Geotextile / Geogrid"
    assert normalize_category("Custom Category") == "Custom Category"


def test_normalize_status_maps_common_aliases() -> None:
    assert normalize_status(None) == "active"
    assert normalize_status("Do Not Use") == "do_not_use"
    assert normalize_status("No Account") == "no_account"
    assert normalize_status("Needs Verification") == "needs_verification"


def test_normalize_import_row_builds_supplier_create() -> None:
    row = SupplierImportRow(
        company=" EMCO ",
        category="pipe",
        secondary_categories="waterworks; ductile iron",
        contact_name="Mike Connolly",
        email="MConnolly@emcoltd.com",
        phone="604-000-0000",
        website="https://example.com",
        branch_location="Abbotsford",
        region="Fraser Valley",
        status="Preferred",
        source="User supplied",
        source_url="https://example.com/contact",
        notes="Default pipe supplier",
    )

    item = normalize_import_row(row, 1)

    assert item.valid is True
    assert item.supplier is not None
    assert item.supplier.name == "EMCO"
    assert item.supplier.category == "Pipe / Utilities"
    assert item.supplier.service_area == "Fraser Valley"
    assert item.supplier.contacts[0].first_name == "Mike"
    assert item.supplier.contacts[0].last_name == "Connolly"
    assert item.supplier.contacts[0].email == "MConnolly@emcoltd.com"
    assert item.supplier.metadata["status"] == "preferred"
    assert item.supplier.metadata["preferred"] is True
    assert item.supplier.metadata["secondary_categories"] == ["Waterworks", "Ductile Iron"]


def test_normalize_import_row_warns_missing_email() -> None:
    row = SupplierImportRow(company="Superior Paving", category="asphalt")

    item = normalize_import_row(row, 2)

    assert item.valid is True
    assert "Missing email" in item.warnings


def test_normalize_import_row_errors_missing_company() -> None:
    row = SupplierImportRow(category="asphalt", email="estimating@example.com")

    item = normalize_import_row(row, 3)

    assert item.valid is False
    assert "Missing company" in item.errors
    assert item.supplier is None


def test_preview_supplier_import_counts_valid_errors_and_warnings() -> None:
    payload = SupplierImportPreviewRequest(
        rows=[
            SupplierImportRow(company="EMCO", category="pipe", email="estimating@example.com"),
            SupplierImportRow(company="No Email", category="asphalt"),
            SupplierImportRow(category="testing", email="bad-email"),
        ]
    )

    result = preview_supplier_import(payload)

    assert result.valid_count == 2
    assert result.error_count == 1
    assert result.warning_count == 1
