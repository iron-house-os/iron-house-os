# Builds 195–200 — Estimating Acceptance Gate

This block closes the first complete estimating workflow.

## Build 195 — Municipality adjustments

Applies percentage and fixed-cost adjustments for supplementary standards, testing, restoration, permits, traffic, and other municipality-driven requirements.

## Build 196 — RFQ readiness

Checks required supplier categories and required package documents before an RFQ package is considered complete.

## Build 197 — Quote recommendation

Ranks complete supplier quotes using scope completeness, exclusions, confidence, and price. Incomplete quotes are not recommended.

## Build 198 — Equipment optimization

Compares equipment options using hourly cost, estimated hours, mobilization, and fuel surcharges.

## Build 199 — Risk and contingency

Calculates expected-value contingency from probability and cost impact while avoiding risks already included in price.

## Build 200 — Bid package acceptance

Produces an adjusted cost, contingency, tender price, blockers, warnings, and final package-ready decision through:

`POST /api/v1/bid-readiness/evaluate`

## Boundary

Municipality requirements must be supplied from reviewed project standards. This build does not claim that every BC municipality standard is automatically current or complete. Supplier pricing and takeoff quantities must pass their existing Build 193 and Build 194 gates before final bid review.

## Validation

Backend installation, Ruff, pytest, frontend installation, lint, tests, and production build must pass. The exact merged `main` baseline must then pass a separate validation PR.
