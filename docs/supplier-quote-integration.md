# Supplier Quote Integration (Build 203)

Build 203 connects supplier quote comparison to estimate line items and workbook export.

## Selection policy

A quote is eligible to price an estimate only when it:

- is marked qualified;
- has status `received` or `selected`; and
- has an amount greater than zero.

For each estimate line item, Iron House OS:

1. ignores superseded revisions of the same supplier quote line;
2. automatically selects the lowest qualified quote when no supplier is manually selected;
3. accepts exactly one manually selected qualified quote;
4. requires a selection reason when the manual choice is above the lowest qualified amount; and
5. blocks estimate handoff when the selection is ambiguous or incomplete.

Unqualified, bounced, declined, rejected, requested, and zero-value quotes remain visible as source records but cannot set estimate pricing.

## API and UI flow

- `POST /api/v1/quotes/compare` applies the shared policy and returns qualified counts, blockers, and readiness.
- `POST /api/v1/quotes/estimate-selection` returns selection decisions plus ready-to-use `EstimateLineItem` records.
- Quote Comparison exposes status, qualification, notes, manual selection, and selection reason.
- **Use selected quotes in estimate** sends ready line items to the Estimating page and retains qualified alternatives.
- Estimate calculation ignores unqualified quotes and falls back to the lowest qualified quote if a non-low choice has no reason.
- The workbook Quote Comparison sheet records qualification, selection, selection reason, qualification notes, and quote notes.

## Queue boundary

This build consumes manually entered supplier quote records. Automated RFQ package creation, quote collection, and mailbox/Drive ingestion remain separate follow-on work.
