from app.schemas.cost_code import CostCodeResolveRequest
from app.schemas.estimate_validation import (
    EstimateValidationIssue,
    EstimateValidationRequest,
    EstimateValidationResult,
    ValidationSeverity,
)
from app.services.cost_codes import resolve_cost_code


def validate_estimate(payload: EstimateValidationRequest) -> EstimateValidationResult:
    issues: list[EstimateValidationIssue] = []
    estimate = payload.estimate

    if not estimate.line_items:
        issues.append(_issue(ValidationSeverity.error, "estimate.empty", "Estimate has no line items."))

    for index, item in enumerate(estimate.line_items):
        resolved = resolve_cost_code(
            CostCodeResolveRequest(code=item.code, description=item.description)
        )
        if payload.require_cost_codes and resolved.match is None:
            issues.append(
                _issue(
                    ValidationSeverity.error,
                    "line_item.cost_code_missing",
                    f"No cost code could be resolved for '{item.description}'.",
                    index,
                    "code",
                )
            )
        elif item.code is None and resolved.match is not None:
            issues.append(
                _issue(
                    ValidationSeverity.warning,
                    "line_item.cost_code_suggested",
                    f"Suggested cost code {resolved.match.code} for '{item.description}'.",
                    index,
                    "code",
                )
            )

        has_price = any(
            [
                item.direct_unit_cost is not None,
                bool(item.labour),
                bool(item.equipment),
                bool(item.materials),
                bool(item.disposal),
                item.subcontract is not None,
                bool(item.vendor_quotes),
                item.default_activity is not None,
            ]
        )
        if payload.require_priced_items and not has_price:
            issues.append(
                _issue(
                    ValidationSeverity.error,
                    "line_item.unpriced",
                    f"'{item.description}' has no pricing basis.",
                    index,
                    "direct_unit_cost",
                )
            )
        if item.quantity == 0:
            issues.append(
                _issue(
                    ValidationSeverity.warning,
                    "line_item.zero_quantity",
                    f"'{item.description}' has zero quantity.",
                    index,
                    "quantity",
                )
            )

    if estimate.markup.profit_percent < payload.minimum_profit_percent:
        issues.append(
            _issue(
                ValidationSeverity.warning,
                "markup.low_profit",
                f"Profit markup is below {payload.minimum_profit_percent:.1f}%.",
                field="markup.profit_percent",
            )
        )
    if not estimate.assumptions:
        issues.append(_issue(ValidationSeverity.warning, "estimate.no_assumptions", "No estimate assumptions recorded."))
    if not estimate.exclusions:
        issues.append(_issue(ValidationSeverity.warning, "estimate.no_exclusions", "No estimate exclusions recorded."))

    errors = sum(issue.severity == ValidationSeverity.error for issue in issues)
    warnings = sum(issue.severity == ValidationSeverity.warning for issue in issues)
    return EstimateValidationResult(is_valid=errors == 0, errors=errors, warnings=warnings, issues=issues)


def _issue(
    severity: ValidationSeverity,
    code: str,
    message: str,
    line_item_index: int | None = None,
    field: str | None = None,
) -> EstimateValidationIssue:
    return EstimateValidationIssue(
        severity=severity,
        code=code,
        message=message,
        line_item_index=line_item_index,
        field=field,
    )
