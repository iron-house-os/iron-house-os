from __future__ import annotations

import re

from app.schemas.supplier import ContactCreate, SupplierCreate
from app.schemas.supplier_import import (
    SupplierImportPreviewItem,
    SupplierImportPreviewRequest,
    SupplierImportPreviewResponse,
    SupplierImportRow,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

STATUS_ALIASES = {
    "": "active",
    "active": "active",
    "preferred": "preferred",
    "needs verification": "needs_verification",
    "needs_verification": "needs_verification",
    "bounced": "bounced",
    "do not use": "do_not_use",
    "do_not_use": "do_not_use",
    "no account": "no_account",
    "no_account": "no_account",
    "archived": "archived",
}

CATEGORY_ALIASES = {
    "pipe": "Pipe / Utilities",
    "pipes": "Pipe / Utilities",
    "waterworks": "Waterworks",
    "ductile iron": "Ductile Iron",
    "manhole": "Manholes / Catch Basins",
    "manholes": "Manholes / Catch Basins",
    "catch basin": "Manholes / Catch Basins",
    "catch basins": "Manholes / Catch Basins",
    "aggregate": "Aggregates",
    "aggregates": "Aggregates",
    "asphalt": "Asphalt",
    "concrete": "Concrete Subcontractor",
    "testing": "Testing / Inspection",
    "coring": "Sawcutting / Coring",
    "sawcutting": "Sawcutting / Coring",
    "traffic": "Traffic Control",
    "traffic control": "Traffic Control",
    "geo": "Geotextile / Geogrid",
    "geotextile": "Geotextile / Geogrid",
}


def preview_supplier_import(payload: SupplierImportPreviewRequest) -> SupplierImportPreviewResponse:
    items = [normalize_import_row(row, index + 1) for index, row in enumerate(payload.rows)]
    return SupplierImportPreviewResponse(
        items=items,
        valid_count=sum(1 for item in items if item.valid),
        error_count=sum(len(item.errors) for item in items),
        warning_count=sum(len(item.warnings) for item in items),
    )


def normalize_import_row(row: SupplierImportRow, row_number: int) -> SupplierImportPreviewItem:
    errors: list[str] = []
    warnings: list[str] = []

    company = _clean(row.company)
    if not company:
        errors.append("Missing company")

    category = normalize_category(row.category)
    if not category:
        warnings.append("Missing category")

    email = _clean(row.email)
    if email and not EMAIL_RE.match(email):
        warnings.append("Invalid email format")
    if not email:
        warnings.append("Missing email")

    status = normalize_status(row.status)
    preferred = bool(row.preferred) or status == "preferred"

    metadata = {
        "status": status,
        "preferred": preferred,
        "secondary_categories": _split_categories(row.secondary_categories),
        "branch_location": _clean(row.branch_location),
        "address": _clean(row.address),
        "source": _clean(row.source),
        "source_url": _clean(row.source_url),
    }

    supplier = None
    if not errors:
        supplier = SupplierCreate(
            name=company or "Unknown Supplier",
            category=category,
            service_area=_clean(row.region),
            website=_clean(row.website),
            notes=_clean(row.notes),
            metadata=metadata,
            contacts=[
                ContactCreate(
                    first_name=_contact_first_name(row.contact_name),
                    last_name=_contact_last_name(row.contact_name),
                    email=email,
                    phone=_clean(row.phone),
                    role="Estimating" if email else None,
                )
            ]
            if email or row.contact_name or row.phone
            else [],
        )

    return SupplierImportPreviewItem(
        row_number=row_number,
        valid=not errors,
        supplier=supplier,
        warnings=warnings,
        errors=errors,
    )


def normalize_category(value: str | None) -> str | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    return CATEGORY_ALIASES.get(cleaned.lower(), cleaned)


def normalize_status(value: str | None) -> str:
    cleaned = (_clean(value) or "active").lower()
    return STATUS_ALIASES.get(cleaned, cleaned.replace(" ", "_"))


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _split_categories(value: str | None) -> list[str]:
    cleaned = _clean(value)
    if not cleaned:
        return []
    parts = re.split(r"[,;/|]+", cleaned)
    return [category for part in parts if (category := normalize_category(part))]


def _contact_first_name(value: str | None) -> str:
    cleaned = _clean(value)
    if not cleaned:
        return "Estimating"
    return cleaned.split()[0]


def _contact_last_name(value: str | None) -> str | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    parts = cleaned.split(maxsplit=1)
    return parts[1] if len(parts) > 1 else None
