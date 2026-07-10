# Repair Gates v2: Builds 47–110

Status: active gated repair continuation.

Rule: do not advance from one build to the next until the current build has a green check.

## Verified ranges

- Builds 47–97: ✅ green.

## Build 98 — MVP acceptance criteria

Gate status: ✅ implementation verified; pending branch CI confirmation.

- Original build commit verified: `9eb9c473c068d08c573f262503c52471975318aa`.
- `docs/build-98-acceptance-criteria.md` exists on the repair branch.
- Acceptance requires project reopen, takeoff persistence, estimate handoff/workspace persistence, RFQ drafts, readiness accuracy, workbook export, and dry-run completion without manual database changes.

Next action: require a green GitHub Actions run before advancing to Build 99.
