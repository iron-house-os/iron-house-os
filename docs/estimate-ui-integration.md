# Estimate UI Integration

## Status

The Estimating page at `/estimating` is connected to the backend estimate engine and workbook export.

Completed capabilities:

- Loads production activity defaults from `GET /api/v1/estimates/rate-library`
- Calculates estimates through `POST /api/v1/estimates/summary`
- Downloads formatted workbooks through `POST /api/v1/estimates/workbook`
- Supports project name and code with required-name validation
- Supports line item quantity, unit, direct unit cost, and production activity defaults
- Supports line-item disposal material, quantity, unit, disposal cost, haul cost, and facility
- Supports a selected vendor quote with supplier, scope, amount, selected flag, and notes
- Supports mobilization, disposal allowance, risk amount, risk probability, contingency, overhead, profit, bonding, and insurance
- Displays bid totals, gross margin, category breakdown, per-line calculated cost, unit cost, and selected supplier
- Blocks calculation and workbook export when the project name is empty

## Validation

The frontend test command runs the real Vitest suite:

```bash
cd frontend
npm test
```

`EstimatingPage.test.tsx` verifies:

- production defaults load from the API
- line item, disposal, quote, risk, and markup data reach the summary endpoint
- the returned bid summary and selected supplier render
- missing project names block summary and workbook requests

## Next Queue Boundary

Multiple supplier quotes, qualified-low selection, and non-low selection reasons remain part of the separate supplier quote integration task in issue #1.
