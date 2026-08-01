# Iron House Labour Charge-Out and Small-Job Standard

**Effective date:** 2026-08-01  
**Owner:** Iron House Contracting Ltd.  
**Function:** Estimating and bids  
**Status:** Approved estimating standard

## Purpose

This standard defines the default labour wage basis, labour charge-out calculation, regional market classification and small-job pricing treatment for Iron House estimates.

## Source and Evidence Limitation

Government of Canada Job Bank wage information updated November 19, 2025 reports the Lower Mainland-Southwest Region as one labour market. The published upper hourly wages used as primary anchors are:

- Construction labourer/helper: **$39.00/hour**.
- Heavy-equipment operator: **$50.00/hour**.
- Construction site supervisor: **$46.00/hour**.

The source does not publish separate civil-construction wage tables for Vancouver and the Fraser Valley. Iron House will therefore keep the markets separate in every estimate, but both markets initially use the same upper-market wage library. Future Iron House payroll, recruiting, project-cost and bid-result data may support separate regional wage libraries.

The 2.1 labour multiplier and small-job premiums are internal Iron House estimating decisions, not published contractor averages.

## Regional Estimating Markets

Every estimate must select one regional market.

### Vancouver / Metro West

Vancouver, Richmond, Burnaby, New Westminster, the North Shore and other Metro Vancouver locations west or north of the Surrey boundary.

### Surrey and Fraser Valley East

Surrey, Langley, Abbotsford, Mission, Chilliwack, Hope and surrounding Fraser Valley communities.

Surrey belongs to the **Surrey and Fraser Valley East** market.

Regional classification is separate from travel, mobilization, parking, accommodation, toll, congestion, restricted-hours and site-access costs. Those costs remain visible estimate lines.

## Upper-Market Wage Library

Use the following base hourly wages for budget and tender estimates unless actual employee wage, collective agreement, prevailing-wage requirement or approved project-specific rate is known.

| Civil role | Default base wage | Basis |
|---|---:|---|
| General labourer | $39.00 | Published regional upper wage anchor |
| Skilled labourer | $43.00 | Internal role mapping above labourer anchor |
| Pipe layer | $47.00 | Internal civil trade mapping |
| Equipment operator | $50.00 | Published regional upper wage anchor |
| Senior operator / grader operator | $55.00 | Internal senior-skill mapping |
| Civil / pipe foreman | $55.00 | Internal leadership mapping above published supervisor anchor |
| General foreman | $62.00 | Internal senior-leadership mapping |

The estimate must identify whether each wage is `published_anchor`, `internal_role_mapping`, or `actual_employee_rate`.

## Standard Labour Charge-Out

```text
Regular labour charge-out rate = base hourly wage x 2.1
```

The 2.1 multiplier is intended to recover employment burden, non-productive time, PPE, training, administration, supervision allocation, company overhead and a target final margin of 10%.

The 10% target is not an additional automatic markup on top of the 2.1 multiplier.

### Standard Regular-Time Charge-Out Library

| Civil role | Base wage | Calculated rate | Customer rate |
|---|---:|---:|---:|
| General labourer | $39.00 | $81.90 | **$82/hour** |
| Skilled labourer | $43.00 | $90.30 | **$90/hour** |
| Pipe layer | $47.00 | $98.70 | **$99/hour** |
| Equipment operator | $50.00 | $105.00 | **$105/hour** |
| Senior operator / grader | $55.00 | $115.50 | **$116/hour** |
| Civil / pipe foreman | $55.00 | $115.50 | **$116/hour** |
| General foreman | $62.00 | $130.20 | **$130/hour** |

Round customer-facing labour rates to the nearest whole dollar.

## Small-Job Definition and Premium

A small job is work planned for five field shifts or fewer.

| Planned duration | Premium | Effective multiplier |
|---|---:|---:|
| 1 field shift | 25% | 2.625x |
| 2-3 field shifts | 20% | 2.520x |
| 4-5 field shifts | 15% | 2.415x |
| More than 5 shifts | 0% | 2.100x |

```text
Small-job labour rate = base hourly wage x 2.1 x (1 + small-job premium)
```

The premium applies only to labour. Mobilization, equipment, rentals, fuel, trucking, disposal, materials and subcontractors remain separate.

## Pricing Rules

1. Use the selected regional market and upper-market wage library by default.
2. Replace a library wage with a known actual wage when the assigned employee or collective requirement is confirmed.
3. Keep Vancouver congestion, parking, restricted-hour and access costs separate from wage rates.
4. Apply the small-job premium only to labour.
5. Existing client agreements, tender schedules and stipulated force-account rates override this standard.
6. Overtime, night work, weekends, remote work and living-out allowances are separate adjustments.
7. Show all overrides and supporting reasons in the estimate summary.

## Estimate Model Fields

- `regional_market`: `vancouver_metro_west` or `surrey_fraser_valley_east`
- `civil_role`
- `wage_basis_type`: `published_anchor`, `internal_role_mapping`, or `actual_employee_rate`
- `base_hourly_wage`
- `labour_chargeout_multiplier`, default `2.1`
- `target_margin_percent`, default `10`
- `planned_field_shifts`
- `small_job_tier`
- `small_job_premium_percent`
- `calculated_labour_chargeout_rate`
- `override_reason`

## Approval Control

A multiplier below 2.1, target margin below 10%, waived small-job premium, or base wage below the approved library requires a written reason and estimator or executive approval.

## Review Cycle

Review wage anchors quarterly and whenever reliable new Job Bank data, union schedules, payroll information, recruiting results or completed-project cost data becomes available.

## Exclusions

This standard does not determine employee compensation, payroll policy, union obligations, prevailing-wage requirements, equipment rates, subcontractor markups, taxes, bonding, contingency or project-specific risk allowances.
