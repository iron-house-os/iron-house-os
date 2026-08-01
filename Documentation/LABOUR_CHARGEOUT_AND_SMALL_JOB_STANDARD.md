# Iron House Labour Charge-Out and Small-Job Standard

**Effective date:** 2026-08-01  
**Owner:** Iron House Contracting Ltd.  
**Function:** Estimating and bids  
**Status:** Approved estimating standard

## Purpose

This standard defines the default labour charge-out calculation and small-job pricing treatment for Iron House estimates. It applies unless a project-specific written approval overrides it.

## Standard Labour Charge-Out

For regular-time labour-only pricing:

```text
Base labour charge-out rate = employee base hourly wage x 2.1
```

The 2.1 multiplier is intended to recover payroll burden, statutory costs, benefits where applicable, non-productive time, PPE, training, administration, supervision allocation, company overhead and a target final margin of 10%.

The 10% target is a final estimate margin target. It is not an additional automatic 10% markup on top of the 2.1 labour multiplier.

Round customer-facing hourly labour rates to the nearest whole dollar unless a contract or bid form requires another convention.

## Small-Job Definition

A small job is work planned for **five field shifts or fewer**, excluding weather shutdowns and owner-caused delays.

Small-job status is determined from the planned field duration at estimate review. It must be recalculated if the planned duration changes materially before submission.

## Small-Job Labour Premium

Apply the following premium to the standard labour charge-out rate:

| Planned field duration | Small-job premium | Effective wage multiplier |
|---|---:|---:|
| 1 field shift | 25% | 2.625x |
| 2-3 field shifts | 20% | 2.520x |
| 4-5 field shifts | 15% | 2.415x |
| More than 5 field shifts | 0% | 2.100x |

Calculation:

```text
Small-job labour rate = base hourly wage x 2.1 x (1 + small-job premium)
```

Example for a labourer earning $32.00/hour:

| Planned duration | Calculation | Charge-out rate |
|---|---:|---:|
| Regular job | $32 x 2.1 | $67.20 -> $68/hour |
| 1 shift | $32 x 2.1 x 1.25 | $84.00/hour |
| 2-3 shifts | $32 x 2.1 x 1.20 | $80.64 -> $81/hour |
| 4-5 shifts | $32 x 2.1 x 1.15 | $77.28 -> $78/hour |

## Pricing Rules

1. Apply the small-job premium to labour charge-out only.
2. Price mobilization and demobilization as separate visible estimate lines.
3. Price equipment, rentals, fuel, trucking, disposal, materials and subcontractors separately.
4. Do not use the small-job premium to hide known scope, access, schedule or risk costs.
5. Overtime, night work, weekends, remote work and living-out allowances are separate adjustments and are not absorbed by this premium.
6. Change-order and emergency work may use a higher approved rate, but the estimator must record the reason.
7. Existing client agreements, tender schedules and stipulated force-account rates override this standard.
8. The estimate summary must show the selected duration tier and resulting premium.

## Estimate Model Fields

The estimating model should include:

- `base_hourly_wage`
- `labour_chargeout_multiplier`, default `2.1`
- `target_margin_percent`, default `10`
- `planned_field_shifts`
- `small_job_tier`
- `small_job_premium_percent`
- `calculated_labour_chargeout_rate`
- `override_reason`, required when defaults are changed

## Approval Control

Any estimate using a labour multiplier below 2.1, a target margin below 10%, or a waived small-job premium requires explicit estimator or executive approval and a written reason in the estimate record.

## Exclusions

This standard does not determine employee compensation, payroll policy, union rates, prevailing wage obligations, equipment charge-out rates, subcontractor markups, taxes, bonding, contingency or project-specific risk allowances.
