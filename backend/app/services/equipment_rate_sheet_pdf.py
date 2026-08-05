from __future__ import annotations

from textwrap import wrap

from app.core.errors import AppError
from app.schemas.equipment_rates import ClientRateSheetRequest
from app.services.equipment_rates import calculate_equipment_rate
from app.services.flha_pdf import _build_pdf


def render_client_rate_sheet_pdf(payload: ClientRateSheetRequest) -> bytes:
    calculated = [(line, calculate_equipment_rate(line)) for line in payload.lines]
    blocked = [result for _, result in calculated if result.approval_required]
    if payload.executive_approved and blocked:
        raise AppError(
            "Executive issue is blocked until all rate exceptions are approved.",
            status_code=409,
        )

    lines: list[str] = []

    def add(value: str = "") -> None:
        lines.extend(wrap(str(value), width=96, break_long_words=False) or [""])

    add("IRON HOUSE CONTRACTING LTD.")
    add(payload.title.upper())
    if payload.executive_approved:
        add(f"APPROVED FOR ISSUE - Reference: {payload.approval_reference}")
    else:
        add("DRAFT - NOT APPROVED FOR EXTERNAL ISSUE")
    add(
        f"Market: {payload.regional_market.value.replace('_', ' ').title()} | "
        f"Effective: {payload.effective_date} | Expires: {payload.expiry_date}"
    )
    add("Currency: CAD | GST excluded unless expressly stated")
    add()

    order = (
        "labour",
        "equipment",
        "attachment",
        "support_vehicle_light_equipment",
        "trucking_disposal",
        "mobilization_logistics",
    )
    for category in order:
        category_lines = [
            (source, result)
            for source, result in calculated
            if source.rate_category.value == category
        ]
        if not category_lines:
            continue
        add(category.replace("_", " ").upper())
        for source, result in category_lines:
            status = "APPROVAL REQUIRED" if result.approval_required else "READY"
            operator = (
                "operator included"
                if source.operator_included
                else "operator priced in all-in rate"
            )
            add(
                f"{source.equipment_class} - {source.equipment_description}: "
                f"${result.selected_client_rate:,.2f}/hr | {operator} | "
                f"minimum ${result.minimum_billable_amount:,.2f} | "
                f"standby ${result.standby_rate:,.2f}/hr | {status}"
            )
            add(
                f"  Basis: {source.rate_basis.value.replace('_', ' ')} | "
                f"Source: {source.source_name or 'not identified'} | "
                f"Calculated minimum: ${result.calculated_client_rate:,.2f}/hr"
            )
            if result.approval_reasons:
                add(f"  Controls: {', '.join(result.approval_reasons)}")
        add()

    add("COMMERCIAL TERMS")
    for term in (
        "Compact equipment and labour-only service calls carry a 4-hour minimum unless a vendor minimum is greater.",
        "Heavy equipment, trucking and subcontracted specialty equipment carry an 8-hour minimum unless quoted otherwise.",
        "Mobilization and demobilization are visible and separate.",
        "Standby caused by Iron House is not billable. Client-caused standby is billable subject to contract.",
        "Operator and attachment inclusion are stated per line. Operator labour must not be added twice.",
        "Fuel surcharge is 0% while the selected benchmark fuel provision is not exceeded.",
        "Contract, tender or stipulated force-account rates take precedence when approved.",
        "Parking, congestion, restricted access, permits, ferries, tolls and accommodation are separate.",
    ):
        add(f"- {term}")

    if payload.qualifications:
        add()
        add("QUALIFICATIONS")
        for item in payload.qualifications:
            add(f"- {item}")
    if payload.exclusions:
        add()
        add("EXCLUSIONS")
        for item in payload.exclusions:
            add(f"- {item}")

    pages = [lines[index : index + 52] for index in range(0, len(lines), 52)] or [[""]]
    return _build_pdf(pages)
