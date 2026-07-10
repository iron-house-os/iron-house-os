# Repair Gates v2: Builds 47–110

Status: active gated repair continuation.

Rule: do not advance from one build to the next until the current build has a green check.

## Verified ranges

- Builds 47–94: ✅ green.

## Build 95 — Pricing assumptions policy

Gate status: ✅ implementation verified; pending branch CI confirmation.

- Original build commit verified: `406fdbfb6c18c9a1006339cf7814e994381dd224`.
- `docs/build-95-pricing-assumptions-policy.md` exists on the repair branch.
- The policy requires explicit assumptions for hours, access, dewatering, shoring, disposal, traffic control, testing, survey, permits, restoration, weather, and exclusions.

Next action: require a green GitHub Actions run before advancing to Build 96.
