from datetime import date

import pytest

from app.schemas.equipment_rates import (
    ApprovalStatus,
    ClientRateSheetRequest,
    EquipmentRateInput,
    RateBasis,
    RateCategory,
    RegionalMarket,
    RentalPeriod,
)
from app.services.equipment_rate_sheet_pdf import render_client_rate_sheet_pdf
from app.services.equipment_rates import calculate_equipment_rate, get_equipment_rate_library


def rate_input(**overrides) -> EquipmentRateInput:
    values = {
        "regional_market": RegionalMarket.surrey_fraser_valley_east,
        "rate_category": RateCategory.equipment,
        "equipment_class": "Excavator",
        "equipment_description": "20-23 t",
        "base_rate": 800,
        "rental_period": RentalPeriod.day,
        "included_hours": 8,
        "operator_hourly_cost": 50,
        "market_benchmark_rate": 228,
        "source_name": "Current vendor quote",
        "source_url": "https://vendor.example/quote",
        "target_margin_percent": 10,
    }
    values.update(overrides)
    return EquipmentRateInput(**values)


def test_library_uses_one_benchmark_set_for_both_markets() -> None:
    library = get_equipment_rate_library()

    assert library.regional_markets == [
        RegionalMarket.vancouver_metro_west,
        RegionalMarket.surrey_fraser_valley_east,
    ]
    assert len(library.benchmarks) == 59
    excavator = next(
        item
        for item in library.benchmarks
        if item.equipment_class == "Excavator"
        and item.equipment_description == "20-23 t"
    )
    assert excavator.base_rate == 228
    assert excavator.operator_included is True


def test_period_conversion_uses_included_hours_and_margin_not_markup() -> None:
    result = calculate_equipment_rate(rate_input(market_benchmark_rate=0))

    assert result.hourly_base_rate == 100
    assert result.hourly_all_in_direct_cost == 150
    assert result.calculated_client_rate == 166.67
    assert result.selected_client_rate == 166.67


def test_selects_greater_of_benchmark_or_calculated_minimum() -> None:
    result = calculate_equipment_rate(rate_input())

    assert result.calculated_client_rate == 166.67
    assert result.selected_client_rate == 228


def test_operator_inclusion_prevents_double_counting() -> None:
    result = calculate_equipment_rate(
        rate_input(
            operator_included=True,
            operator_hourly_cost=75,
            market_benchmark_rate=0,
        )
    )

    assert result.hourly_all_in_direct_cost == 100
    assert result.operator_labour_to_add == 0


def test_zero_fuel_surcharge_and_attachment_are_auditable() -> None:
    result = calculate_equipment_rate(
        rate_input(
            base_rate=800,
            damage_waiver_percent_or_amount=10,
            fuel_surcharge_percent=0,
            attachment_rate=25,
            delivery_cost=80,
            pickup_cost=80,
            market_benchmark_rate=0,
        )
    )

    assert result.audit_components["damage_waiver"] == 80
    assert result.audit_components["fuel_surcharge"] == 0
    assert result.audit_components["attachment_hourly"] == 25
    assert result.hourly_rental_direct_cost == 155


def test_standby_and_minimum_charge_are_explicit() -> None:
    result = calculate_equipment_rate(
        rate_input(
            standby_rate=120,
            minimum_billable_hours=8,
            market_benchmark_rate=200,
        )
    )

    assert result.standby_rate == 120
    assert result.minimum_billable_amount == 1600


def test_contract_rate_overrides_default_but_below_benchmark_needs_approval() -> None:
    result = calculate_equipment_rate(
        rate_input(
            rate_basis=RateBasis.contract_rate,
            contract_rate=190,
            market_benchmark_rate=228,
            override_reason="Tender force-account rate",
        )
    )

    assert result.selected_client_rate == 190
    assert result.approval_required is True
    assert "selected_rate_below_benchmark" in result.approval_reasons


def test_approved_override_without_written_reason_stays_blocked() -> None:
    result = calculate_equipment_rate(
        rate_input(
            rate_basis=RateBasis.contract_rate,
            contract_rate=190,
            market_benchmark_rate=228,
            approval_status=ApprovalStatus.approved,
        )
    )

    assert result.approval_required is True
    assert "override_reason_required" in result.approval_reasons


def test_approved_override_clears_gate_without_hiding_reasons() -> None:
    result = calculate_equipment_rate(
        rate_input(
            rate_basis=RateBasis.contract_rate,
            contract_rate=190,
            market_benchmark_rate=228,
            override_reason="Approved tender force-account rate",
            approval_status=ApprovalStatus.approved,
        )
    )

    assert result.approval_required is False
    assert "selected_rate_below_benchmark" in result.approval_reasons


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"target_margin_percent": 9}, "margin_below_10_percent"),
        ({"waive_mobilization": True}, "mobilization_waived"),
        ({"waive_minimum": True}, "minimum_charge_waived"),
        ({"operator_inclusion_changed": True}, "operator_inclusion_changed"),
        ({"quote_expiry_date": date(2026, 1, 1)}, "vendor_quote_expired"),
        ({"source_name": ""}, "source_or_class_missing"),
    ],
)
def test_controlled_exceptions_require_reason_and_approval(overrides, reason) -> None:
    result = calculate_equipment_rate(
        rate_input(**overrides),
        as_of=date(2026, 8, 5),
    )

    assert result.approval_required is True
    assert reason in result.approval_reasons
    assert "override_reason_required" in result.approval_reasons


def test_client_rate_sheet_defaults_to_draft_watermark() -> None:
    payload = ClientRateSheetRequest(
        effective_date=date(2026, 8, 5),
        expiry_date=date(2026, 9, 4),
        regional_market=RegionalMarket.surrey_fraser_valley_east,
        lines=[rate_input()],
    )

    pdf = render_client_rate_sheet_pdf(payload)

    assert pdf.startswith(b"%PDF-1.4")
    assert b"DRAFT - NOT APPROVED FOR EXTERNAL ISSUE" in pdf



def test_client_cannot_self_declare_executive_approval() -> None:
    with pytest.raises(ValueError, match="executive_approved"):
        ClientRateSheetRequest(
            effective_date=date(2026, 8, 5),
            expiry_date=date(2026, 9, 4),
            regional_market=RegionalMarket.surrey_fraser_valley_east,
            lines=[rate_input()],
            executive_approved=True,
        )
