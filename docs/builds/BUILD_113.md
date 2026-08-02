# Build 113 — Enhanced mobile FLHA

Issue: #113

## Delivered scope

- Replaced the generic FLHA entry path with a phone-first Field Level Hazard Assessment workflow in the foreperson portal and linked Safety > Field Forms to that system-of-record flow.
- Added available-data prefill, ten Yes / No / N/A screening items, repeatable task-hazard-control-owner rows, hierarchy-of-controls categories, company presets, reusable project presets, emergency response fields, and shared IHOS photo attachments.
- Added backend release blockers for missing required fields and uncontrolled critical hazards, crew-scoped own-device or supervised shared-device signatures, immutable signed/released versions, versioned re-assessment, supervisor field-verification release, audit events, and compact PDF export.
- Kept AI outside the safety decision: stored FLHAs explicitly record that automated suggestions do not determine safety or completion.

## Validation evidence

- `PATH=/tmp/ihos-113-python/local/bin:$PATH PYTHONPATH=/tmp/ihos-113-python/local/lib/python3.12/dist-packages bash scripts/test.sh`
  - Ruff: passed.
  - Backend: 210 passed, 1 pre-existing Pydantic warning.
  - Frontend TypeScript lint: passed.
  - Frontend production build: passed; existing bundle-size advisory remains.
- `npm run test -- src/components/FlhaWorkflow.test.tsx`: 1 passed.
- `python3 scripts/check_visual_design_lock.py`: passed for all 13 protected files against baseline `3c6cbe89`.
- `python3 scripts/check_react_router_rsc_boundary.py --root .`: passed; no RSC dependencies or source APIs.
- Mobile Chromium evidence at 390 px viewport: body `scrollWidth` 390 / `clientWidth` 390; no horizontal overflow. Screenshot: [issue-113-flha-mobile.png](../evidence/issue-113-flha-mobile.png).

The optional full frontend Vitest run completed 48 of 49 tests. The unrelated existing RFQ builder test exceeded its 5-second timeout when run in the full suite; its isolated rerun passed 2 of 2. No timeout or approval gate was changed.

## Safety, security, and production review

- Critical hazards require an accepted control, responsible person, and any marked-required evidence before signatures or release.
- Every listed crew member must sign the exact version before supervisor release.
- Viewer PDF access is limited to listed crew and forepersons; edit, re-assessment, shared-device signature supervision, and release require foreperson or management authority.
- No production files, data, secrets, payment/invitation functions, deployment configuration, or approval gates were changed. This remains staging-only until acceptance testing passes.

## Rollback

Revert the issue #113 commit. Existing non-FLHA field records and database schema remain unchanged because the workflow uses the existing `field_records` JSON, signature, document, status, and audit-compatible fields.
