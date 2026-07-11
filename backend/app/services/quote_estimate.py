from collections import defaultdict

from app.schemas.cost_code import CostCodeResolveRequest
from app.schemas.quote_integration import (
    QuoteEstimateImportRequest,
    QuoteEstimateImportResponse,
    QuoteEstimateLine,
    QuoteRevisionSummary,
    SupplierQuoteCreate,
)
from app.services.cost_codes import resolve_cost_code


def import_quotes_to_estimate(payload: QuoteEstimateImportRequest) -> QuoteEstimateImportResponse:
    current_quotes, revisions = _select_current_revisions(
        payload.quotes,
        payload.include_superseded_revisions,
    )
    lines: list[QuoteEstimateLine] = []
    warnings: list[str] = []

    for quote in current_quotes:
        resolution = resolve_cost_code(
            CostCodeResolveRequest(
                code=quote.line_item_code,
                description=quote.line_item_description or quote.scope,
            )
        )
        match = resolution.match
        needs_review = match is None or resolution.confidence < payload.minimum_mapping_confidence
        if quote.amount == 0:
            needs_review = True
            warnings.append(
                f"{quote.supplier_name}: '{quote.scope}' has a zero amount and requires review."
            )
        if quote.exclusions:
            warnings.append(
                f"{quote.supplier_name}: '{quote.scope}' includes {len(quote.exclusions)} exclusion(s)."
            )

        lines.append(
            QuoteEstimateLine(
                supplier_name=quote.supplier_name,
                quote_reference=quote.quote_reference,
                revision=quote.revision,
                scope=quote.scope,
                scope_type=quote.scope_type,
                amount=quote.amount,
                cost_code=match.code if match else None,
                cost_code_name=match.name if match else None,
                mapping_confidence=resolution.confidence,
                needs_review=needs_review,
                exclusions=quote.exclusions,
                notes=quote.notes,
            )
        )

    return QuoteEstimateImportResponse(
        lines=lines,
        revisions=revisions,
        mapped_count=sum(1 for line in lines if line.cost_code and not line.needs_review),
        review_count=sum(1 for line in lines if line.needs_review),
        total_amount=round(sum(line.amount for line in lines), 2),
        warnings=sorted(set(warnings)),
    )


def _select_current_revisions(
    quotes: list[SupplierQuoteCreate],
    include_superseded: bool,
) -> tuple[list[SupplierQuoteCreate], list[QuoteRevisionSummary]]:
    grouped: dict[tuple[str, str], list[SupplierQuoteCreate]] = defaultdict(list)
    for quote in quotes:
        key = (
            quote.supplier_name.strip().lower(),
            (quote.quote_reference or quote.scope).strip().lower(),
        )
        grouped[key].append(quote)

    selected: list[SupplierQuoteCreate] = []
    summaries: list[QuoteRevisionSummary] = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda quote: quote.revision)
        current = ordered[-1]
        superseded = [quote.revision for quote in ordered[:-1]]
        summaries.append(
            QuoteRevisionSummary(
                supplier_name=current.supplier_name,
                quote_reference=current.quote_reference,
                current_revision=current.revision,
                superseded_revisions=superseded,
            )
        )
        selected.extend(ordered if include_superseded else [current])

    selected.sort(key=lambda quote: (quote.supplier_name.lower(), quote.scope.lower(), quote.revision))
    summaries.sort(key=lambda item: (item.supplier_name.lower(), item.quote_reference or ""))
    return selected, summaries
