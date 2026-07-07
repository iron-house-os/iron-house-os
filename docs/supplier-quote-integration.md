# Supplier Quote Integration

## Purpose

Supplier quote integration connects RFQ responses to estimate line items so Iron House can compare pricing, select qualified suppliers, and preserve the reasoning when the lowest quote is not selected.

## Backend Additions

New schemas:

- `SupplierQuoteCreate`
- `SupplierQuoteRead`
- `QuoteComparisonRequest`
- `QuoteComparisonResponse`
- `QuoteComparisonLine`

New service:

- `backend/app/services/quote_comparison.py`

New endpoint:

- `POST /api/v1/quotes/compare`

## Selection Rule

The comparison service groups quotes by line item and scope.

Default behavior:

1. Select the lowest quote if no quote is manually marked selected.
2. Respect the manually selected quote when `is_selected` is true.
3. Preserve `selection_reason` when the selected quote is not the lowest.
4. Report the delta between lowest-total and selected-total.

## Quote Fields

Each quote can track:

- RFQ ID
- RFQ package ID
- Supplier ID
- Supplier name
- Estimate line item code
- Estimate line item description
- Scope
- Scope type
- Status
- Amount
- Selected flag
- Selection reason
- Exclusions
- Notes

## Next Database Migration

The existing `quotes` table is basic. A future Alembic migration should add:

- `rfq_package_id UUID REFERENCES rfq_packages(id)`
- `line_item_code VARCHAR(80)`
- `line_item_description VARCHAR(255)`
- `scope VARCHAR(255)`
- `scope_type VARCHAR(80)`
- `is_selected BOOLEAN NOT NULL DEFAULT FALSE`
- `selection_reason TEXT`
- `exclusions_json JSONB NOT NULL DEFAULT '[]'`
- `metadata_json JSONB NOT NULL DEFAULT '{}'`

## Estimating Integration

Estimate line items already support `vendor_quotes` as input. The estimate engine uses:

- manually selected quote when present
- otherwise lowest quote

This allows supplier responses to update estimate pricing without rewriting the estimate structure.
