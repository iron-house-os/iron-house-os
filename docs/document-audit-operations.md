# Document Audit Operations

## Purpose

Document Operations records upload, token issuance, signed download, direct download, and denied signed-download activity. The audit panel provides recent-event filtering, operational totals, action distribution, request correlation IDs, and CSV export.

## Operator workflow

1. Open **Document Operations**.
2. Use the Action, Outcome, Actor, or Project UUID filters to narrow the investigation.
3. Select **Load activity** to refresh both the event table and summary counts.
4. Review request IDs when tracing one transaction across application logs.
5. Select **Export CSV** to preserve the currently filtered view.
6. Select **Reset** before beginning a separate investigation.

## Investigation guidance

- Repeated `signed_download` events with outcome `denied` may indicate expired, malformed, or tampered tokens.
- Use Project UUID filtering when reviewing an RFQ package or tender-specific document flow.
- Use Actor filtering to identify activity associated with a user, supplier, or automation identity.
- Compare the summary action distribution with the event table before exporting evidence.

## Current retention boundary

The recent-event buffer is bounded and process-local. It is intended for current operational visibility, not permanent compliance retention. A persistent audit store remains the production path for long-term evidence and cross-instance aggregation.

## Green-gate requirement

Changes to audit capture, filtering, summaries, or exports must pass backend lint/tests and frontend lint/tests/build before merge.
