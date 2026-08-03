# Issue 136 stabilization audit evidence

Date: 2026-08-03 UTC
Issue: [#136](https://github.com/iron-house-os/iron-house-os/issues/136)
Audited `main`: `bfb1508fc00a239dbd7dc30a303c684827762e78`
Authorized staging release: `bd8af914245ce5fb141abcc697dcd9081ab2c084`

## Outcome

The focused code checks found no reproducible Critical or High application
defect in the five priority workflows. The authorized staging host is healthy,
but it is not running the authorized release. Its readiness response reports
`e9cde294b366d500c6e0f0746e0e0a474f859f58`, which is 49 commits behind the
authorized release and predates the current FLHA, media authorization, receipt,
and foreman time-sheet work.

Owner acceptance testing is **blocked** until an authorized staging operator
deploys the already approved staging release and provides staging-only role
accounts through the protected credential channel. No production system or
credential was accessed or changed during this audit.

## Reproducible defects

### IHOS-136-01 — High — authorized staging host runs a stale release

- Steps: request `https://staging.os.ironhousecivil.com/readiness` without a
  session and inspect `checks.deployment_environment` and `release_id`; compare
  the release with
  `docs/operations/staging-deployment-request-2026-08-02.md`.
- Expected: environment `staging` at authorized release `bd8af914245ce5fb141abcc697dcd9081ab2c084`.
- Actual: HTTP 200 and environment `staging`, but release
  `e9cde294b366d500c6e0f0746e0e0a474f859f58`.
- Affected roles/devices: every staging role on phone, tablet, and desktop;
  the deployed revision predates workflows required by issue #136.
- Evidence: `/readiness` returned 200 with database and document storage ready;
  `/health` returned 200; `git merge-base --is-ancestor` confirmed the deployed
  release is an ancestor of the authorized release; `git rev-list --count`
  measured 49 intervening commits.
- Disposition: **Blocked — owner/operator action required.** Repository policy
  prohibits this agent from deploying or modifying the staging host. Use the
  approved staging-only procedure already recorded in
  `docs/operations/staging-deployment-request-2026-08-02.md`. Do not use any
  production Compose file, environment, host, or credential.

## Acceptance matrix

`Passed` below means the listed automated evidence passed against current code.
It does not substitute for the required authenticated shared-staging smoke.

| Existing workflow | Status | Evidence or blocker |
| --- | --- | --- |
| Login, sessions, roles, permissions, navigation | Blocked | Focused backend/frontend checks passed; exact-HEAD CI browser shell passed. Authenticated shared-staging smoke is blocked by stale release and unavailable staging-only role accounts. |
| Projects, tenders, estimating, RFQs, suppliers, procurement, documents | Blocked | Focused API/UI tests passed; disposable release smoke passed on the current code ancestor. Shared staging is 49 commits behind the authorized release. |
| FLHA and field records: create, edit, sign, release, audit, PDF, media | Blocked | Focused API/UI tests passed, including signature and media authorization coverage. The deployed staging release predates the current FLHA stabilization work. |
| Foreman daily time sheets: create, approve, revise, export/post, conflicts | Blocked | Focused API/UI tests passed. The deployed staging release predates the time-sheet implementation. |
| Receipt capture, review, approval/export, media controls | Blocked | Focused API/UI tests passed. The deployed staging release predates the receipt workflow. |
| Finance/admin screens already present | Passed | Full backend and frontend unit suites passed; browser navigation/accessibility passed in exact-HEAD CI. Live authenticated staging remains outside this status. |
| Browser, mobile, responsive overflow, accessibility | Passed | Exact-HEAD GitHub CI browser/mobile/accessibility job passed. Local launch was environment-blocked before page load because the sandbox lacks Playwright system libraries. |
| Security boundaries | Passed | Backend role/media authorization tests, React Router RSC boundary checker, and visual lock passed. `npm audit --omit=dev` reports the already documented GHSA-qwww-vcr4-c8h2 monitored exception; the enforced check found no RSC dependency, API, or source path. |
| Migrations and disposable stack | Passed | Release Readiness passed staging isolation, Alembic upgrade, disposable staging, and full release smoke on authorized ancestor `bd8af91`. Current `main` adds only the staging deployment request. |
| Backup, restore, rollback, release evidence | Passed | Release Readiness passed backup/restore sentinel verification, rollback-boundary verification, and immutable evidence generation on `bd8af91`. |
| Authenticated shared-staging core workflow smoke | Blocked | The shared host is stale and no staging-only test credentials were available. No credential workaround was attempted. |
| Physical iPad acceptance | Deferred | Requires an authorized staging release, staging-only account, and owner/device acceptance session. |

## Exact executed evidence

### Focused priority checks

- Backend: `102 passed, 1 warning in 72.00s`.
- Frontend: `9 passed` test files, `22 passed` tests in `31.67s`.

The focused backend selection covered authentication, login security, role
permissions, projects, tenders, suppliers, documents, RFQ packages, FLHA,
field operations, media and document authorization, daily time sheets, and
receipts. The frontend selection covered the application shell, login, project
workspace, estimating, RFQ builder, FLHA, daily time sheets, receipt capture,
and universal photos.

### Full local code gates

- `ruff check`: passed.
- Backend `pytest -q`: `225 passed, 1 warning in 91.52s`.
- Visual design lock: passed, 13 protected files, baseline `3c6cbe89`.
- React Router RSC boundary: passed; 106 files scanned, RSC dependencies and
  source APIs absent, locked router version 7.18.2.
- Frontend TypeScript lint: passed.
- Frontend Vitest: `19 passed` test files, `53 passed` tests in `82.43s`.
- Frontend production build: passed; 1,860 modules transformed.
- `npm audit --omit=dev`: two High findings for the documented conditional
  React Router RSC advisory; applicability control passed as described above.
- Local Playwright: blocked before application launch. All 33 cases reported
  missing host libraries (Chromium first failed on `libatk-1.0.so.0`; WebKit
  listed the missing GUI/media libraries). No test assertion executed.

The Python runner lacked `pip`, `venv`, and a `python` alias, so locked backend
dependencies were installed under `/tmp` and Python-based gates used
`python3`. The sandbox also had no Docker executable.

### GitHub and staging evidence

- Exact-HEAD CI run
  [30776108755](https://github.com/iron-house-os/iron-house-os/actions/runs/30776108755):
  backend, frontend, and browser/mobile/accessibility jobs all passed for
  `bfb1508fc00a239dbd7dc30a303c684827762e78`.
- Release Readiness run
  [30775902683](https://github.com/iron-house-os/iron-house-os/actions/runs/30775902683):
  all six jobs passed for authorized release
  `bd8af914245ce5fb141abcc697dcd9081ab2c084`, including disposable staging,
  browser/mobile/accessibility, migrations, backup/restore, rollback, and
  release evidence. Current `main` differs only by the staging deployment
  request document.
- Anonymous live staging on 2026-08-03 UTC: `/readiness` 200, `/health` 200,
  `/` 200; reported release `e9cde294b366d500c6e0f0746e0e0a474f859f58`.

## Required owner/operator actions

1. Deploy the already authorized release to the staging-only host with the
   approved operator procedure; confirm the readiness `release_id` exactly.
2. Supply individual staging-only representative role accounts through the
   protected credential mechanism. Do not place credentials in the issue, PR,
   repository, logs, or acceptance record.
3. Run the authenticated five-workflow staging smoke and record representative
   record IDs plus role-denial evidence.
4. Complete physical iPad acceptance after the automated and shared-staging
   checks pass.

## Recommendation

The current code is ready for deployment to isolated staging based on the
focused and release evidence. The current shared staging system is **not ready
for owner acceptance testing** because it is running the wrong release. No
application repair is justified until acceptance is rerun against the
authorized build and a defect is reproduced there.
