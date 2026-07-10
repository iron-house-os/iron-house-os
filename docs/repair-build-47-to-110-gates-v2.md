# Repair Gates v2: Builds 47–110

Status: active gated repair continuation.

Rule: do not advance from one build to the next until the current build has a green check.

The original repair branch was deleted after Build 46. This continuation branch restores the verified audit trail and continues from `main`.

## Restored verified gates

- Build 47 — Compose health checks: ✅ green. Evidence: GitHub Actions run `29050502542` passed backend and frontend jobs.
- Build 48 — Deployment checklist: ✅ green. File: `docs/deployment-checklist.md`.
- Build 49 — MVP test plan: ✅ green. File: `docs/mvp-test-plan.md`.
- Build 50 — Web app MVP bridge documentation: ✅ green. File: `docs/build-36-to-50-web-app-mvp.md`.
- Build 51 — MVP workflow page: ✅ green. File: `frontend/src/pages/MVPWorkflowPage.tsx`.
- Build 52 — MVP workflow route: ✅ green. File: `frontend/src/App.tsx`.
- Build 53 — MVP workflow module card: ✅ green. File: `frontend/src/modules.ts`.

CI evidence for restored gates: run `29044918254` completed successfully on the previous repair branch state.

## Build 54 — System readiness service

Gate status: ✅ green.

- `backend/app/services/system_readiness.py` exists.
- Reports status `ready`, service name, API prefix, and enabled MVP service checks.

## Build 55 — Shared readiness endpoint

Gate status: ✅ green.

- `backend/app/main.py` imports and calls `get_system_readiness()` for `GET /readiness`.

## Build 56 — System readiness tests

Gate status: ✅ green.

- `tests/backend/test_system_readiness.py` verifies readiness status and enabled takeoff, estimate, RFQ, and project-readiness checks.

## Build 57 — Operator runbook

Gate status: ✅ green.

- `docs/operator-runbook.md` documents startup, bid workflow, recovery, and first-live-use controls.

## Build 58 — First live bid checklist

Gate status: ✅ green.

- `docs/first-live-bid-checklist.md` covers project setup, takeoff, estimate, RFQs, and final review.

## Build 59 — MVP status record

Gate status: ✅ green.

- `docs/mvp-status.md` records working backend/frontend paths, remaining MVP work, deferred items, and estimator-controlled first-live-use guidance.
- Build commit verified: `79ac95a88bd50958e14c0e35ed2a2e838f761987`.

## Build 60 — Operating layer documentation

Gate status: ✅ green.

- `docs/build-51-to-60-operating-layer.md` registers Builds 51–60, summarizes the operating layer, and identifies Builds 61–65 as the next work.
- Build commit verified: `679be0837ba29686cec32b3b46f94cd0056d23ff`.

Green check evidence for Builds 54–60:

- GitHub Actions run `29103011695` completed successfully.
- GitHub Actions run `29103156739` completed successfully after the final audit-log update.
- Backend checks passed: install, Ruff lint, pytest.
- Frontend checks passed: install, lint/type gate, smoke test gate, Vite build.

## Build 61 — Takeoff save panel

Gate status: ✅ green.

- Original build commit verified: `6576702aac13c14ee0911a39328a01cdcf7e6d6c`.
- `frontend/src/components/TakeoffSavePanel.tsx` exists on the repair branch.
- The panel requires an active project, saves current items and quantity register through `takeoffPersistenceApi`, reports errors, and confirms the saved takeoff ID.
- GitHub Actions run `29104528761` completed successfully.

## Build 62 — Wire takeoff save panel

Gate status: ✅ green.

- Original build commit verified: `50cea6072eb5b4665c3ad13d712b2d1aa79c9dcc`.
- `frontend/src/pages/QuantityTakeoffPage.tsx` imports and renders `TakeoffSavePanel`.
- Active quantity items are calculated once and passed to both the takeoff engine and save panel.
- The current quantity summary is passed as the quantity register for persistence.
- GitHub Actions run `29104711599` completed successfully.

## Build 63 — Saved takeoffs panel

Gate status: ✅ green.

- Original build commit verified: `90ccf404e674ae228db15d12bfcbf925b2a48294`.
- `frontend/src/components/SavedTakeoffsPanel.tsx` exists on the repair branch.
- The panel requires an active project, loads saved takeoffs through `takeoffPersistenceApi.listForProject`, displays loading and error states, and renders saved takeoff records or an empty state.
- GitHub Actions run `29105013536` completed successfully.

## Build 64 — Saved estimate workspaces panel

Gate status: ✅ green.

- Original build commit verified: `5bee536814856bb3ef35fa506cb556c069d42636`.
- `frontend/src/components/SavedEstimateWorkspacesPanel.tsx` exists on the repair branch.
- The panel requires an active project, loads saved estimate workspaces through `estimateWorkspaceApi.listForProject`, reports loading and error states, and renders saved workspaces or an empty state.
- GitHub Actions run `29105273661` completed successfully.

## Build 65 — Project operations page

Gate status: ✅ green.

- Original build commit verified: `326cd02c6e25960e70af722dc29df70d0164099e`.
- `frontend/src/pages/ProjectOperationsPage.tsx` exists on the repair branch.
- The page accepts a project ID and combines project readiness, saved takeoffs, and saved estimate workspaces in one operating view.
- GitHub Actions run `29105643021` completed successfully.

## Build 66 — Route project operations page

Gate status: ✅ green.

- Original build commit verified: `73e2b1c4aca1d598c4afde2d31729b600a928ef9`.
- `frontend/src/App.tsx` imports `ProjectOperationsPage`.
- `/project-operations` is excluded from placeholder routing and renders the project operations page.
- GitHub Actions run `29105926742` completed successfully.

## Build 67 — Project operations module card

Gate status: ✅ green.

- Original build commit verified: `9bad1eebc2ab58751ff92535f217d6057001581d`.
- `frontend/src/modules.ts` includes the Project Operations module card at `/project-operations` using `FolderKanban`.
- Quantity Takeoff status reflects Build 62.
- GitHub Actions run `29106206710` completed successfully.

## Build 68 — Backend smoke check script

Gate status: ✅ green.

- Original build commit verified: `1cc54dfcd64b9694c6d37532b2182f37cd87796e`.
- `scripts/smoke_check.py` exists on the repair branch.
- The script checks `/health`, `/readiness`, and `/api/v1/projects`, prints JSON summaries, and exits nonzero when checks fail.
- GitHub Actions run `29106431583` completed successfully.

## Build 69 — UI operations documentation

Gate status: ✅ green.

- Original build commit verified: `dfe867ad83872bd6ba1cac3806cd1049ce2f76dd`.
- `docs/build-61-to-70-ui-operations.md` exists on the repair branch.
- The document summarizes Builds 61–69, the resulting project operations flow, and the remaining manual project-ID gap.
- GitHub Actions run `29106838748` completed successfully.

## Build 70 — Cutover note

Gate status: ✅ implementation verified; pending branch CI confirmation.

- Original build commit verified: `25cda1c77d86d87322321199800a9176da383c49`.
- `docs/build-70-cutover-note.md` exists on the repair branch.
- The note defines local operator-testing cutover conditions and preserves mandatory estimator review.

Next action: require a green GitHub Actions run before advancing to Build 71.
