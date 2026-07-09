# Repair Gates: Builds 43–110

Status: active gated repair pass.

Rule: do not advance from one build to the next until the current build has a green check.

## Build 43 — CI workflow hardening

Gate status: pending GitHub check.

Verification target:

- CI workflow has backend and frontend jobs.
- Backend job installs dev dependencies, runs Ruff, then pytest.
- Frontend job installs with npm ci, runs lint, test, and build.
- Workflow can be triggered on push, pull request, and manual workflow dispatch.

Evidence already inspected:

- `.github/workflows/ci.yml` includes `workflow_dispatch`.
- `.github/workflows/ci.yml` includes strict backend lint/test and frontend lint/test/build checks.

Next action after green check: inspect and repair Build 44 only.
