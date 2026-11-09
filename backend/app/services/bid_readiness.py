from app.schemas.bid_readiness import BidReadinessRequest, BidReadinessResponse, RankedOption


def evaluate_bid_readiness(payload: BidReadinessRequest) -> BidReadinessResponse:
    municipality_cost = round(
        sum(payload.direct_cost * item.percentage / 100 + item.fixed_cost for item in payload.municipality_adjustments),
        2,
    )
    adjusted_cost = round(payload.direct_cost + municipality_cost, 2)

    missing_categories = sorted(set(payload.rfq.required_categories) - set(payload.rfq.covered_categories))
    missing_documents = sorted(set(payload.rfq.required_documents) - set(payload.rfq.attached_documents))
    rfq_ready = not missing_categories and not missing_documents

    recommended_quote = _recommend_quote(payload)
    recommended_equipment = _recommend_equipment(payload)
    contingency = round(
        sum(item.probability * item.impact for item in payload.risks if not item.included_in_price),
        2,
    )

    blockers: list[str] = []
    warnings: list[str] = []
    if payload.direct_cost <= 0:
        blockers.append("Direct cost must be greater than zero.")
    if missing_categories:
        blockers.append("RFQ coverage is incomplete.")
    if missing_documents:
        blockers.append("Required RFQ documents are missing.")
    if payload.quotes and recommended_quote is None:
        blockers.append("No supplier quote is suitable for award.")
    if not payload.assumptions:
        warnings.append("Bid assumptions have not been recorded.")
    if not payload.exclusions:
        warnings.append("Bid exclusions have not been recorded.")
    for adjustment in payload.municipality_adjustments:
        if adjustment.requirement and adjustment.percentage == 0 and adjustment.fixed_cost == 0:
            warnings.append(f"Municipal requirement needs pricing review: {adjustment.requirement}")

    tender_price = round((adjusted_cost + contingency) * (1 + payload.markup_percentage / 100), 2)
    package_ready = not blockers and bool(payload.assumptions) and bool(payload.exclusions)
    return BidReadinessResponse(
        municipality_cost=municipality_cost,
        adjusted_cost=adjusted_cost,
        contingency=contingency,
        recommended_quote=recommended_quote,
        recommended_equipment=recommended_equipment,
        rfq_ready=rfq_ready,
        missing_rfq_categories=missing_categories,
        missing_rfq_documents=missing_documents,
        tender_price=tender_price,
        package_ready=package_ready,
        blockers=blockers,
        warnings=warnings,
    )


def _recommend_quote(payload: BidReadinessRequest) -> RankedOption | None:
    ranked: list[RankedOption] = []
    for quote in payload.quotes:
        if not quote.scope_complete or quote.amount <= 0:
            continue
        penalty = quote.exclusions_count * 5 + (1 - quote.confidence) * 20
        score = round(100 - penalty, 2)
        warnings = []
        if quote.exclusions_count:
            warnings.append(f"{quote.exclusions_count} exclusions require review.")
        ranked.append(RankedOption(name=quote.supplier, total_cost=quote.amount, score=score, warnings=warnings))
    if not ranked:
        return None
    return sorted(ranked, key=lambda item: (-float(item.score or 0), item.total_cost, item.name))[0]


def _recommend_equipment(payload: BidReadinessRequest) -> RankedOption | None:
    options = [
        RankedOption(
            name=item.name,
            total_cost=round(item.hourly_rate * item.estimated_hours + item.mobilization + item.fuel_surcharge, 2),
        )
        for item in payload.equipment
        if item.estimated_hours > 0
    ]
    if not options:
        return None
    return sorted(options, key=lambda item: (item.total_cost, item.name))[0]
