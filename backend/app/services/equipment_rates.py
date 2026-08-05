from __future__ import annotations

from datetime import date

from app.schemas.equipment_rates import (
    ApprovalStatus,
    EquipmentBenchmark,
    EquipmentRateInput,
    EquipmentRateLibrary,
    EquipmentRateResult,
    RateBasis,
    RateCategory,
    RegionalMarket,
    RentalPeriod,
)

_SOURCE_NAME = "IEOA 2026 Suggested Equipment Rates"
_SOURCE_URL = "https://www.ieoa.ca/rates/"
_SOURCE_DATE = date(2026, 1, 1)

_EQUIPMENT_ROWS: tuple[tuple[str, str, float], ...] = (
    ("Excavator", "1.4-2.75 t", 142),
    ("Excavator", "2.75-4 t", 163),
    ("Excavator", "4-6 t", 169),
    ("Excavator", "6-9.5 t", 180),
    ("Excavator", "9.5-14 t", 193),
    ("Excavator", "14-19 t", 205),
    ("Excavator", "20-23 t", 228),
    ("Excavator", "23-26 t", 248),
    ("Excavator", "26-30 t", 257),
    ("Excavator", "30-36 t", 287),
    ("Skid steer", "Under 1,000 lb operating load", 112),
    ("Skid steer", "1,000-2,000 lb operating load", 124),
    ("Skid steer", "2,000-3,200 lb operating load", 143),
    ("Compact track loader", "Under 1,100 lb operating load", 121),
    ("Compact track loader", "1,100-2,230 lb operating load", 146),
    ("Compact track loader", "2,230-3,000 lb operating load", 151),
    ("Compact track loader", "3,000-3,225 lb operating load", 154),
    ("Loader/backhoe", "80-100 HP extendahoe", 165),
    ("Loader/backhoe", "100-108 HP extendahoe", 187),
    ("Bulldozer", "Under 80 HP", 195),
    ("Bulldozer", "80-125 HP", 228),
    ("Bulldozer", "125-220 HP", 282),
    ("Wheel loader", "Under 1.75 yd3", 184),
    ("Wheel loader", "2-2.5 yd3", 205),
    ("Wheel loader", "3 yd3", 249),
    ("Vibratory compactor", "Up to 4.9 t", 184),
    ("Vibratory compactor", "5-7.9 t", 195),
    ("Vibratory compactor", "8-11.9 t", 219),
    ("Grader", "Under 80 HP", 184),
    ("Grader", "85-90 HP", 205),
    ("Grader", "125-135 HP", 219),
    ("Grader", "135-150 HP", 249),
    ("Dump truck", "Single axle, 7-8 t", 141),
    ("Dump truck", "Tandem, 13-14 t", 165),
    ("Dump truck", "Tridem, 20 t", 175),
    ("Dump truck", "Tandem and pup, 25-27 t", 219),
    ("Dump truck", "Tandem and tri-axle pup, 29-31 t", 228),
    ("Off-road rock truck", "20 ton", 231),
    ("Off-road rock truck", "25 ton", 249),
    ("Off-road rock truck", "30 ton", 266),
    ("Slinger truck", "Tandem, 13-14 t", 205),
    ("Slinger truck", "Tridem, 20 t", 213),
    ("Lowbed with tandem tractor", "20 ton", 179),
    ("Lowbed with tandem tractor", "30 ton", 184),
    ("Lowbed with tandem tractor", "40 ton", 202),
)

_ATTACHMENT_ROWS: tuple[tuple[str, str, float], ...] = (
    ("Hydraulic hammer", "Approx. 13,000 lb excavator", 109),
    ("Hydraulic hammer", "Approx. 22,000 lb excavator", 128),
    ("Hydraulic hammer", "Approx. 25,000 lb excavator", 143),
    ("Hydraulic hammer", "Approx. 38,000 lb excavator", 155),
    ("Hydraulic hammer", "Approx. 45,000 lb excavator", 174),
    ("Compactor attachment", "5 t excavator or rubber-tired backhoe", 47),
    ("Compactor attachment", "7-10 t excavator", 58),
    ("Compactor attachment", "20 t excavator", 79),
)


def get_equipment_rate_library() -> EquipmentRateLibrary:
    benchmarks = [
        EquipmentBenchmark(
            rate_category=RateCategory.equipment,
            equipment_class=category,
            equipment_description=description,
            base_rate=rate,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            source_effective_date=_SOURCE_DATE,
        )
        for category, description, rate in _EQUIPMENT_ROWS
    ]
    benchmarks.extend(
        EquipmentBenchmark(
            rate_category=RateCategory.attachment,
            equipment_class=category,
            equipment_description=description,
            base_rate=rate,
            operator_included=False,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            source_effective_date=_SOURCE_DATE,
        )
        for category, description, rate in _ATTACHMENT_ROWS
    )
    for category, description in (
        ("Excavator", "Over 36 t"),
        ("Bulldozer", "Over 290 HP"),
        ("Wheel loader", "Over 6 yd3"),
        ("Vibratory compactor", "Over 12 t"),
        ("Lowbed", "Over 50 t"),
        ("Specialized crane", "Vendor-priced class"),
    ):
        benchmarks.append(
            EquipmentBenchmark(
                rate_category=RateCategory.equipment,
                equipment_class=category,
                equipment_description=description,
                base_rate=None,
                source_name=_SOURCE_NAME,
                source_url=_SOURCE_URL,
                source_effective_date=_SOURCE_DATE,
                price_on_request=True,
            )
        )
    return EquipmentRateLibrary(
        regional_markets=list(RegionalMarket),
        benchmarks=benchmarks,
    )


def calculate_equipment_rate(
    payload: EquipmentRateInput,
    *,
    as_of: date | None = None,
) -> EquipmentRateResult:
    current_date = as_of or date.today()
    divisor = payload.included_hours if payload.rental_period != RentalPeriod.hour else 1
    base_period_cost = payload.base_rate
    waiver = (
        base_period_cost * payload.damage_waiver_percent_or_amount / 100
        if payload.damage_waiver_is_percent
        else payload.damage_waiver_percent_or_amount
    )
    surcharge = base_period_cost * payload.fuel_surcharge_percent / 100
    allocated_period_cost = (
        base_period_cost
        + waiver
        + payload.rental_fees
        + payload.fuel_cost
        + surcharge
        + payload.delivery_cost
        + payload.pickup_cost
        + payload.cleanup_allowance
    )
    hourly_base_rate = base_period_cost / divisor
    hourly_rental_direct_cost = allocated_period_cost / divisor + payload.attachment_rate
    operator_cost = 0 if payload.operator_included else payload.operator_hourly_cost
    hourly_all_in_direct_cost = (
        hourly_rental_direct_cost + operator_cost + payload.project_support_hourly_cost
    )
    calculated_client_rate = hourly_all_in_direct_cost / (
        1 - payload.target_margin_percent / 100
    )
    benchmark = payload.market_benchmark_rate or 0
    if payload.rate_basis == RateBasis.contract_rate:
        selected_client_rate = payload.contract_rate or 0
    else:
        selected_client_rate = max(benchmark, calculated_client_rate)

    reasons = _approval_reasons(
        payload,
        selected_client_rate=selected_client_rate,
        benchmark=benchmark,
        current_date=current_date,
    )
    approval_required = bool(reasons) and (
        payload.approval_status != ApprovalStatus.approved
        or "override_reason_required" in reasons
    )
    minimum_billable_amount = (
        0 if payload.waive_minimum else selected_client_rate * payload.minimum_billable_hours
    )
    components = {
        "base_rate": base_period_cost,
        "damage_waiver": waiver,
        "rental_fees": payload.rental_fees,
        "fuel": payload.fuel_cost,
        "fuel_surcharge": surcharge,
        "attachment_hourly": payload.attachment_rate,
        "overtime_hour_rate": payload.overtime_hour_rate,
        "delivery": payload.delivery_cost,
        "pickup": payload.pickup_cost,
        "cleanup": payload.cleanup_allowance,
        "operator_hourly": operator_cost,
        "support_hourly": payload.project_support_hourly_cost,
        "mobilization": 0 if payload.waive_mobilization else payload.mobilization_rate,
    }
    return EquipmentRateResult(
        hourly_base_rate=_money(hourly_base_rate),
        hourly_rental_direct_cost=_money(hourly_rental_direct_cost),
        hourly_all_in_direct_cost=_money(hourly_all_in_direct_cost),
        calculated_client_rate=_money(calculated_client_rate),
        selected_client_rate=_money(selected_client_rate),
        minimum_billable_amount=_money(minimum_billable_amount),
        standby_rate=_money(payload.standby_rate),
        operator_labour_to_add=0,
        approval_required=approval_required,
        approval_reasons=reasons,
        approval_status=payload.approval_status,
        source_name=payload.source_name,
        audit_components={key: _money(value) for key, value in components.items()},
    )


def _approval_reasons(
    payload: EquipmentRateInput,
    *,
    selected_client_rate: float,
    benchmark: float,
    current_date: date,
) -> list[str]:
    reasons: list[str] = []
    if benchmark and selected_client_rate < benchmark:
        reasons.append("selected_rate_below_benchmark")
    if payload.target_margin_percent < 10:
        reasons.append("margin_below_10_percent")
    if payload.waive_mobilization:
        reasons.append("mobilization_waived")
    if payload.waive_minimum:
        reasons.append("minimum_charge_waived")
    if payload.operator_inclusion_changed:
        reasons.append("operator_inclusion_changed")
    if payload.quote_expiry_date and payload.quote_expiry_date < current_date:
        reasons.append("vendor_quote_expired")
    if not payload.source_name.strip() or not payload.equipment_class.strip():
        reasons.append("source_or_class_missing")
    if reasons and not (payload.override_reason or "").strip():
        reasons.append("override_reason_required")
    return reasons


def _money(value: float) -> float:
    return round(value + 1e-9, 2)
