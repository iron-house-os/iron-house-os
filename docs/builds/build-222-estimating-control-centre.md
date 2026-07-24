# Build 222 — Estimating Control Centre

## Objective
Turn the existing Iron House estimating module into the company system of record for tender pricing, workbook export, production control, and estimate-to-actual reconciliation.

## Current state
The OS already supports project-scoped estimates, direct-cost build-ups, vendor quotes, production-rate defaults, indirect costs, risk, markups, estimate summaries, saved workspaces, and workbook export.

## Phase 1 — Estimate structure and review controls

### Deliverables
- Add estimate maturity state: Concept, Budget, Tender, Change estimate.
- Add controlled status: Not started, Ready, In progress, Blocked, At risk, Complete, Cancelled.
- Add bid basis fields: client, project, location, bid form, submission time, contract type, bonding, insurance, schedule, bid validity, drawings, specifications, addenda, geotechnical and site information.
- Add scope matrix states: Included, Excluded, By others, Allowance, Alternate, Open.
- Add review gates for scope, quantities, production, vendor coverage, schedule/logistics, risk/contingency, clarifications/exclusions, arithmetic and executive approval.
- Add approval record with approver, date, conditions and evidence.

### Failure controls
- Do not allow a Tender estimate to be represented as submission-ready while a required review gate is open.
- Flag missing vendor quote expiry, freight, tax, lead time or exclusions.
- Separate baseline, current forecast, actual, variance and approved change.
- Do not convert a verbal direction into contract value.

## Phase 2 — Cost libraries and production engine

### Deliverables
- Labour classifications, burdened rates and overtime rules.
- Equipment ownership/rental rates, fuel, mobilization and standby.
- Material catalogue with preferred supplier, freight, waste and escalation.
- Subcontractor and vendor quote levelling.
- Production assemblies for excavation, pipe, bedding, backfill, structures, granulars, concrete, asphalt, landscaping and traffic control.
- Historical production and cost feedback from completed projects.

## Phase 3 — Workbook and Google Sheets output

### Standard workbook tabs
1. Bid Summary
2. Detailed Estimate
3. Quantity Takeoff
4. Labour
5. Equipment
6. Materials
7. Supplier Quotes
8. Subcontractors
9. Production Rates
10. Schedule
11. Cash Flow
12. Risk Register
13. Markups & Profit
14. Onsite Production Control
15. Estimate vs Actual
16. Assumptions
17. Final Tender Summary

### Workbook rules
- The OS database is the system of record.
- Workbooks are generated outputs, not parallel master databases.
- Quantities are entered once and referenced by cost, schedule and field-control outputs.
- Every generated workbook includes version, project, estimate state, approval status and export timestamp.

## Phase 4 — Project handoff and field control

### Deliverables
- Convert awarded estimate items into project cost-code budgets.
- Publish production targets to foreman controls.
- Capture installed quantity, crew hours, equipment hours, loads, tickets and daily notes.
- Calculate earned production, unit-cost variance and forecast-to-complete.
- Reconcile commitments, invoices and actual costs through Financial Control.

## Phase 5 — Bid intelligence

### Deliverables
- Independent arithmetic review.
- Missing-scope and quote-gap detection.
- Risk heat map and contingency recommendation.
- Historical benchmark comparison.
- Alternate pricing and award-likelihood scenarios.
- Tender-package generation with clarifications, exclusions and approvals.

## Approval gate
No estimate may be issued externally or marked Tender Complete without explicit authorized approval and recorded evidence.

## System of record
Iron House OS estimating workspace and project financial ledger.

## Build status
In progress.
