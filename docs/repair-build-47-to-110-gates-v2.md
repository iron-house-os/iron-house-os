# Repair Gates v2: Builds 47–110

Status: active gated repair continuation.

Rule: do not advance from one build to the next until the current build has a green check.

## Verified ranges

- Builds 47–92: ✅ green.

## Build 93 — Estimator review policy

Gate status: ✅ implementation verified; pending branch CI confirmation.

- Original build commit verified: `b387ff98d98d71bae7bb9feb0bfe4c7f2d9beb37`.
- `docs/build-93-estimator-review-policy.md` exists on the repair branch.
- The policy requires estimator review of revisions, quantities, rates, quote scope, self-perform/subcontract splits, risk allowances, bonding, exclusions, and final price.

Next action: require a green GitHub Actions run before advancing to Build 94.
