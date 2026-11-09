from app.schemas.estimate import EstimateCreate, EstimateLineItem, EstimateMarkup
from app.schemas.estimate_validation import EstimateValidationRequest
from app.services.estimate_validation import validate_estimate


def test_validation_rejects_empty_estimate() -> None:
    result = validate_estimate(
        EstimateValidationRequest(estimate=EstimateCreate(project_name="Empty"))
    )
    assert result.is_valid is False
    assert any(issue.code == "estimate.empty" for issue in result.issues)


def test_validation_flags_unpriced_item_and_suggests_cost_code() -> None:
    estimate = EstimateCreate(
        project_name="Storm repair",
        line_items=[EstimateLineItem(description="Install storm pipe", quantity=25)],
    )
    result = validate_estimate(EstimateValidationRequest(estimate=estimate))
    assert result.is_valid is False
    assert any(issue.code == "line_item.unpriced" for issue in result.issues)
    assert any(issue.code == "line_item.cost_code_suggested" for issue in result.issues)


def test_validation_accepts_priced_coded_item() -> None:
    estimate = EstimateCreate(
        project_name="Excavation",
        line_items=[
            EstimateLineItem(
                code="02-200",
                description="Common excavation",
                quantity=100,
                direct_unit_cost=18,
            )
        ],
        markup=EstimateMarkup(profit_percent=10),
        assumptions=["Normal soil conditions"],
        exclusions=["Contaminated soil"],
    )
    result = validate_estimate(EstimateValidationRequest(estimate=estimate))
    assert result.is_valid is True
    assert result.errors == 0


def test_validation_warns_on_zero_quantity_and_low_profit() -> None:
    estimate = EstimateCreate(
        project_name="Allowance",
        line_items=[
            EstimateLineItem(
                code="01-100",
                description="Mobilization",
                quantity=0,
                direct_unit_cost=1000,
            )
        ],
        markup=EstimateMarkup(profit_percent=2),
    )
    result = validate_estimate(
        EstimateValidationRequest(estimate=estimate, minimum_profit_percent=5)
    )
    codes = {issue.code for issue in result.issues}
    assert "line_item.zero_quantity" in codes
    assert "markup.low_profit" in codes
