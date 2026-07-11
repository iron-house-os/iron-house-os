# Build 193 — Supplier Quote to Estimate Integration

Status: implemented; awaiting CI and merged-main validation.

## Delivered
- Imports supplier quote pricing into estimate-ready line records.
- Maps quote scope to the Build 191 cost-code catalog.
- Supports explicit line-item codes and description-based resolution.
- Retains quote revision summaries and uses the latest revision by default.
- Flags unmapped or low-confidence items for estimator review.
- Preserves exclusions and warns on zero pricing.
- Exposes `POST /api/v1/quotes/estimate-import`.

## Boundary
This build normalizes quote data already supplied to the API. Automated parsing of arbitrary PDF quotations and mailbox ingestion remain separate connector and document-processing tasks.
