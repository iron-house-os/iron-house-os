# Build 190 — Procurement Workflow Acceptance

Status: ready for CI validation

Build 190 closes the tender-to-estimating procurement slice.

## Acceptance scenario
1. Register a tender.
2. Confirm linked project and RFQ package creation.
3. Add drawings, specifications, and an addendum.
4. Confirm the drawing index identifies current and superseded sheets.
5. Select suppliers by trade and generate a versioned RFQ attachment manifest.
6. Record sent, due, reminder, received, and declined states.
7. Register at least two supplier quotes and one revision.
8. Compare price, inclusions, exclusions, alternates, lead time, and validity.
9. Confirm dashboard metrics link to source records.
10. Mark the package ready for estimating only when unresolved scope gaps are acknowledged.

## Merge gate
- Backend install, Ruff, and pytest pass.
- Frontend install, lint, tests, and production build pass.
- Builds 181–189 are present in order.
- No document claims that automatic supplier email delivery or BC Bid scraping is live before those connectors are enabled.

Build 191 remains locked until this branch and the merged-main baseline are green.
