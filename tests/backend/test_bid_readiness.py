from app.schemas.bid_readiness import (
    BidReadinessRequest,
    EquipmentCandidate,
    MunicipalityAdjustment,
    QuoteCandidate,
    RFQReadinessInput,
    RiskItem,
)
from app.services.bid_readiness import evaluate_bid_readiness


def test_bid_readiness_builds_complete_tender_gate() -> None:
    result = evaluate_bid_readiness(
        BidReadinessRequest(
            project_name="Marine Drive",
            direct_cost=100000,
            markup_percentage=30,
            municipality_adjustments=[
                MunicipalityAdjustment(
                    municipality="Surrey",
                    label="Supplementary standards",
                    percentage=2,
                    fixed_cost=1500,
                    requirement="Additional testing and restoration controls",
                )
            ],
            rfq=RFQReadinessInput(
                required_categories=["pipe", "asphalt"],
                covered_categories=["pipe", "asphalt"],
                required_documents=["drawings", "specifications"],
                attached_documents=["drawings", "specifications"],
            ),
            quotes=[
                QuoteCandidate(supplier="EMCO", amount=18000, scope_complete=True, confidence=0.98),
                QuoteCandidate(supplier="Alternate", amount=17000, scope_complete=True, exclusions_count=4),
            ],
            equipment=[
                EquipmentCandidate(name="Rental A", hourly_rate=160, estimated_hours=80, mobilization=1200),
                EquipmentCandidate(name="Rental B", hourly_rate=150, estimated_hours=80, mobilization=2500),
            ],
            risks=[RiskItem(label="Unknown subgrade", probability=0.25, impact=20000)],
            assumptions=["Normal working hours"],
            exclusions=["Contaminated soil disposal"],
        )
    )

    assert result.municipality_cost == 3500
    assert result.adjusted_cost == 103500
    assert result.contingency == 5000
    assert result.recommended_quote is not None
    assert result.recommended_quote.name == "EMCO"
    assert result.recommended_equipment is not None
    assert result.recommended_equipment.name == "Rental A"
    assert result.rfq_ready is True
    assert result.package_ready is True
    assert result.tender_price == 141050


def test_bid_readiness_blocks_incomplete_rfq_package() -> None:
    result = evaluate_bid_readiness(
        BidReadinessRequest(
            project_name="Storage Shed",
            direct_cost=50000,
            rfq=RFQReadinessInput(
                required_categories=["concrete", "testing"],
                covered_categories=["concrete"],
                required_documents=["drawings"],
                attached_documents=[],
            ),
        )
    )

    assert result.rfq_ready is False
    assert result.missing_rfq_categories == ["testing"]
    assert result.missing_rfq_documents == ["drawings"]
    assert result.package_ready is False
    assert "RFQ coverage is incomplete." in result.blockers
    assert "Required RFQ documents are missing." in result.blockers


def test_bid_readiness_skips_incomplete_supplier_quotes() -> None:
    result = evaluate_bid_readiness(
        BidReadinessRequest(
            project_name="Bike Path",
            direct_cost=25000,
            quotes=[QuoteCandidate(supplier="Incomplete", amount=10000, scope_complete=False)],
            assumptions=["Traffic windows confirmed"],
            exclusions=["Night work"],
        )
    )

    assert result.recommended_quote is None
    assert "No supplier quote is suitable for award." in result.blockers
