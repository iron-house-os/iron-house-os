from collections import Counter

from app.schemas.bid_package import (
    BidPackageChecklistItem,
    BidPackageGenerateRequest,
    BidPackageGenerateResponse,
    BidPackageInputItem,
    BidPackageSection,
    BidPackageSummary,
)

REQUIRED_SECTIONS: list[BidPackageSection] = [
    "executive_summary",
    "scope_of_work",
    "assumptions",
    "exclusions",
    "risks",
    "municipality_requirements",
    "quantities",
    "rfq_status",
    "supplier_coverage",
    "documents",
]

DEFAULT_ASSUMPTIONS = [
    "Pricing is based on the drawings, specifications, addenda, and information available at bid time.",
    "Work is assumed to proceed during normal working hours unless otherwise stated.",
    "Unknown utilities, contaminated soils, and unsuitable subgrade are excluded unless specifically carried as allowances.",
]

DEFAULT_EXCLUSIONS = [
    "Design, engineering, permits, bonds, and third-party fees unless specifically included.",
    "Hazardous materials handling and contaminated soil disposal unless identified in the tender package.",
    "Work outside the documented project limits unless directed by written change order.",
]


def generate_bid_package(payload: BidPackageGenerateRequest) -> BidPackageGenerateResponse:
    items_by_section = {item.section: item for item in payload.items}
    checklist = [_checklist_item(section, items_by_section.get(section)) for section in REQUIRED_SECTIONS]
    counts = Counter(item.status for item in checklist)
    readiness_score = round((counts["ready"] / len(REQUIRED_SECTIONS)) * 100)
    missing_items = [item.title for item in checklist if item.status == "missing"]
    warnings: list[str] = []

    if payload.estimated_price is None:
        warnings.append("Estimated price is not set.")
    if payload.bid_due_date is None:
        warnings.append("Bid due date is not set.")
    if counts["missing"]:
        warnings.append("Bid package has missing required sections.")
    if counts["needs_review"]:
        warnings.append("Bid package has sections requiring estimator review.")

    summary = BidPackageSummary(
        project_name=payload.project_name,
        municipality=payload.municipality,
        bid_due_date=payload.bid_due_date,
        estimated_price=payload.estimated_price,
        readiness_score=readiness_score,
        ready_count=counts["ready"],
        needs_review_count=counts["needs_review"],
        missing_count=counts["missing"],
    )

    return BidPackageGenerateResponse(
        summary=summary,
        executive_summary=_executive_summary(payload, readiness_score),
        scope_of_work=_section_lines(items_by_section, "scope_of_work", ["Civil construction scope to be confirmed against tender documents."]),
        assumptions=_section_lines(items_by_section, "assumptions", DEFAULT_ASSUMPTIONS),
        exclusions=_section_lines(items_by_section, "exclusions", DEFAULT_EXCLUSIONS),
        risks=_section_lines(items_by_section, "risks", ["Municipal requirements, RFQ coverage, schedule constraints, and unknown site conditions require review before submission."]),
        checklist=checklist,
        missing_items=missing_items,
        warnings=warnings,
    )


def _checklist_item(section: BidPackageSection, item: BidPackageInputItem | None) -> BidPackageChecklistItem:
    if item is None:
        return BidPackageChecklistItem(section=section, title=_section_title(section), status="missing", note="Required section has not been provided.")
    note = item.content or "Provided, but estimator review is still recommended."
    return BidPackageChecklistItem(section=section, title=item.title, status=item.status, note=note)


def _section_lines(items_by_section: dict[BidPackageSection, BidPackageInputItem], section: BidPackageSection, defaults: list[str]) -> list[str]:
    item = items_by_section.get(section)
    if item and item.content:
        return [line.strip() for line in item.content.split("\n") if line.strip()]
    return defaults


def _executive_summary(payload: BidPackageGenerateRequest, readiness_score: int) -> str:
    price = f" Estimated price: ${payload.estimated_price:,.2f}." if payload.estimated_price is not None else " Estimated price is not set."
    due = f" Bid due: {payload.bid_due_date}." if payload.bid_due_date else " Bid due date is not set."
    municipality = f" Municipality: {payload.municipality}." if payload.municipality else " Municipality is not set."
    return f"{payload.project_name} bid package readiness is {readiness_score}%.{municipality}{due}{price} Review all missing and needs-review sections before submission."


def _section_title(section: BidPackageSection) -> str:
    return section.replace("_", " ").title()
