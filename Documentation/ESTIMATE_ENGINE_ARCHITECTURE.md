# Estimate Engine Architecture

This document defines the Iron House OS estimate engine: how project quantities become labour, equipment, materials, subcontractor costs, overhead, profit, contingency, and a final bid price.

## 1. Purpose

The estimate engine should create consistent civil construction bids using Iron House assumptions, supplier quotes, subcontractor pricing, municipal standards, and production-based costing.

It is designed for early-stage Iron House operations where the company self-performs core civil work using a small crew and rented equipment while subcontracting specialized scopes.

## 2. Estimate Flow

```text
Tender Documents
    ↓
Drawing Review
    ↓
Municipal Standards Review
    ↓
Quantity Takeoff
    ↓
Scope Classification
    ↓
Self-Perform Cost Build
    ↓
Supplier / Subcontractor Quote Integration
    ↓
Risk, Overhead, Profit, and Contingency
    ↓
Bid Review
    ↓
Final Submission Price
```

## 3. Core Estimate Objects

The estimate engine should be organized around these objects:

| Object | Description |
| --- | --- |
| Project | Tender-level data such as name, location, owner, close date, and documents. |
| Scope Item | A work item such as excavation, pipe install, asphalt, testing, or concrete. |
| Quantity | Measured or tender-provided amount for a scope item. |
| Production Rate | Expected output per crew per hour/day. |
| Labour Crew | Workers and hourly burdened rates. |
| Equipment Spread | Owned or rented equipment with hourly/daily cost. |
| Material Input | Supplier material item and unit cost. |
| Subcontract Quote | External quote tied to a scope item. |
| Indirect Cost | Mobilization, supervision, traffic, ESC, permits, testing, and project overhead. |
| Risk Allowance | Cost for uncertainty, constructability risk, or incomplete information. |
| Markup | Overhead and profit applied at the bid level or scope level. |

## 4. Required Inputs

- Project information.
- Tender form / schedule of prices.
- Civil drawings.
- Specifications.
- Addenda.
- Municipal standards review.
- Quantity takeoff.
- Supplier quotes.
- Subcontractor quotes.
- Labour rate table.
- Equipment rental rate table.
- Material price table.
- Production rate table.
- Overhead assumptions.
- Profit target.
- Contingency rules.

## 5. Default Execution Model

Unless overridden, the estimate engine assumes Iron House self-performs:

- Mobilization support.
- Utility locates coordination.
- Excavation.
- Trenching.
- Pipe installation.
- Manholes and catch basins.
- Backfill and compaction.
- Subgrade preparation.
- Granular sub-base and base.
- Topsoil and general restoration.
- Cleanup and general earthworks.

Default subcontracted scopes:

- Concrete formwork and finishing.
- Fine grading for asphalt.
- Asphalt paving.
- Pavement markings.
- Street lighting and electrical.
- Specialty testing.
- Coring and sawcutting where required.

## 6. Cost Build Method

Each self-perform item should be calculated as:

```text
Direct Cost = Labour Cost + Equipment Cost + Material Cost + Trucking + Disposal + Testing + Small Tools / Consumables
```

Each production-based item should calculate:

```text
Hours = Quantity / Production Rate
Labour Cost = Hours × Crew Hourly Cost
Equipment Cost = Hours × Equipment Hourly Cost
```

Unit cost:

```text
Unit Cost = Direct Cost / Quantity
```

Sell price:

```text
Sell Price = Direct Cost + Indirects + Risk + Overhead + Profit
```

## 7. Labour Model

The labour table should include:

| Field | Notes |
| --- | --- |
| Role | Foreman, operator, labourer, driver, etc. |
| Base Rate | Hourly wage. |
| Burden | Payroll burden, benefits, statutory costs. |
| Billable / Cost Rate | Fully burdened cost rate. |
| Overtime Rule | Standard, overtime, double time, weekend, night shift. |

Default small crew examples:

- Foreman / operator.
- Excavator operator.
- Skid steer operator.
- Pipe layer.
- Labourer.
- Truck driver, if self-performed.

## 8. Equipment Model

The equipment table should include:

| Field | Notes |
| --- | --- |
| Equipment | Excavator, skid steer, plate tamper, roller, pickup, etc. |
| Owned / Rented | Current assumption. |
| Hourly Cost | Internal or rental-based. |
| Daily Cost | Rental daily rate where applicable. |
| Weekly Cost | Rental weekly rate where applicable. |
| Delivery / Pickup | Mobilization cost. |
| Fuel | Included or separate. |
| Operator Included | Yes/no. |

Year-one planning should account for rented production equipment and company overhead for two GMC Denali 3500 pickup trucks when applicable.

## 9. Material Model

Material costs should support:

- Supplier quote pricing.
- Assumed default pricing.
- Unit conversion.
- Waste factors.
- Delivery charges.
- Minimum order charges.
- Fuel surcharge.
- Environmental fees.
- Lead time notes.
- Approved municipal material restrictions.

Material source priority:

1. Project-specific supplier quote.
2. Current supplier price list.
3. Recent comparable bid quote.
4. Iron House assumed default.
5. Estimator manual input.

## 10. Subcontractor Quote Model

Subcontractor quotes should capture:

| Field | Notes |
| --- | --- |
| Subcontractor | Company name. |
| Scope | Work covered. |
| Quote Amount | Total or unit pricing. |
| Inclusions | Included items. |
| Exclusions | Excluded items. |
| Validity | Quote expiry. |
| Schedule | Availability or duration. |
| Attachments | Quote file path. |
| Risk Notes | Gaps, assumptions, missing items. |

Subcontract quote priority:

1. Compliant quote with full scope.
2. Quote with exclusions priced separately.
3. Budget quote.
4. Assumed pricing.
5. No-bid warning.

## 11. Municipal Standards Cost Impacts

The municipal standards checklist should feed the estimate by adding or adjusting:

- Approved material costs.
- Trench bedding and backfill costs.
- Pavement restoration limits.
- Testing frequencies.
- Permit costs.
- Traffic-control costs.
- ESC costs.
- Working-hour restrictions.
- Inspection hold points.
- Submittal and closeout requirements.
- Schedule duration.
- Risk allowance.

## 12. Indirect Costs

Indirect costs should include:

- Mobilization and demobilization.
- Site supervision.
- Project management.
- Layout and survey.
- Utility locates and daylighting.
- Permits.
- Traffic control.
- Environmental controls.
- Temporary works.
- Testing and inspection.
- Small tools.
- Safety and PPE.
- Site signage.
- Administrative closeout.

## 13. Risk and Contingency

Risk should be assessed by scope item and at the bid level.

Typical risk triggers:

- Incomplete drawings.
- Conflicting notes.
- Missing geotechnical information.
- Unknown utilities.
- Groundwater.
- Contaminated or unsuitable material.
- Tight schedule.
- Restricted work hours.
- Heavy traffic exposure.
- Unknown restoration limits.
- Missing supplier coverage.
- Unresolved RFIs.

Risk treatment options:

- Price contingency.
- Bid qualification.
- Exclusion.
- Allowance.
- RFI before close.
- No-bid recommendation.

## 14. Markup Logic

The engine should allow markup by:

- Global project percentage.
- Scope category.
- Self-perform work.
- Subcontracted work.
- Materials only.
- Risk-adjusted bid strategy.

Minimum markup outputs:

- Direct cost.
- Indirect cost.
- Subtotal before contingency.
- Contingency.
- Overhead.
- Profit.
- Final bid price.
- Gross margin percentage.

## 15. Bid Review Outputs

Each completed estimate should produce:

- Estimate summary.
- Scope breakdown.
- Unit-price table.
- Supplier quote log.
- Subcontractor quote log.
- Assumptions.
- Exclusions.
- RFIs.
- Risk register.
- Cash-flow warning.
- Bid/no-bid recommendation.
- Final submission checklist.

## 16. Workbook Sheet Structure

The first production workbook should use these sheets:

```text
00_Project_Info
01_Tender_Schedule
02_Takeoff
03_Production_Rates
04_Labour_Rates
05_Equipment_Rates
06_Materials
07_Subcontractor_Quotes
08_Supplier_Quotes
09_Indirects
10_Risk_Register
11_Estimate_Build
12_Summary
13_Assumptions_Exclusions
14_RFQ_Log
```

## 17. Validation Rules

The estimate engine should flag:

- Quantity with no unit cost.
- Unit cost with no source.
- Self-perform item with no production rate.
- Equipment item with no rate.
- Labour role with no burdened rate.
- Subcontract scope with no quote or assumed price.
- Supplier quote past validity.
- Missing municipal standards review.
- Missing traffic-control allowance.
- Missing testing allowance.
- Missing contingency.
- Negative or zero sell price.

## 18. Phase 1 Build Target

Phase 1 should support:

1. Manual quantity entry.
2. Manual production-rate selection.
3. Labour and equipment cost build.
4. Supplier and subcontract quote entry.
5. Overhead, profit, and contingency calculations.
6. Summary output.
7. Assumptions and exclusions output.
8. RFQ log link.
9. Basic validation warnings.

## 19. Future Build Targets

Later versions should add:

- Drawing-assisted quantity extraction.
- Automatic supplier quote extraction from emails.
- Historical production-rate benchmarking.
- Bid comparison dashboard.
- Municipality-specific cost modifiers.
- Cash-flow forecasting.
- Equipment ownership versus rental analysis.
- Tender close calendar integration.
- Automated post-bid review.
