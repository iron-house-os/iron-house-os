# Build 191 — Estimate Foundation

Build 191 adds a versioned civil-construction cost-code foundation used by the estimating workflow.

## Implemented
- Typed cost-code groups and records.
- Versioned Iron House civil cost-code library.
- Default estimate item type and unit for each code.
- Deterministic exact-code and description-based resolution.
- `GET /api/v1/cost-codes` and `POST /api/v1/cost-codes/resolve` endpoints.
- Regression tests for uniqueness, core scopes, exact resolution, descriptive resolution, and validation.

## Boundary
This build establishes classification. Estimate persistence, quote import, production calculations, municipality adjustments, qualifications, and package review remain Builds 192–200.
