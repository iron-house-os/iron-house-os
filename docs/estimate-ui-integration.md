# Estimate UI Integration

## Current State

The frontend already has an Estimating page wired into the app route at `/estimating`.

Existing capabilities:

- Loads production rate library from `GET /api/v1/estimates/rate-library`
- Builds an estimate payload
- Calculates estimate summary through `POST /api/v1/estimates/summary`
- Downloads estimate workbook through `POST /api/v1/estimates/workbook`
- Supports project name and code
- Supports line item quantity, unit, direct unit cost, and default production activity
- Supports mobilization, risk allowance, contingency, overhead, profit, bonding, and insurance
- Displays final bid summary and gross margin

## Next UI Improvements

Add the remaining estimate engine fields to the Estimating page:

1. Disposal inputs
   - Material
   - Quantity
   - Unit
   - Disposal unit cost
   - Haul cost
   - Facility

2. Vendor quote inputs
   - Supplier
   - Scope
   - Amount
   - Selected quote flag
   - Notes

3. Risk probability
   - Allow risk amount and probability to calculate expected risk value

4. Category breakdown display
   - Labour
   - Equipment
   - Material
   - Disposal
   - Subcontract
   - Indirect
   - Risk

5. Validation and UX
   - Prevent workbook download when project name is empty
   - Show selected quote supplier beside line item result
   - Add clear note when the lowest quote is not selected

## Implementation Notes

Frontend estimate API types should include `DisposalInput` and `EstimateLineItem.disposal` so the UI matches the backend schema.

Backend workbook export is already available at `/api/v1/estimates/workbook`.
