# React Router RSC security applicability record

## Control record

- Advisory: `GHSA-qwww-vcr4-c8h2`
- Review date: 2026-07-29
- Release candidate: Version 1.0 staging acceptance
- Production baseline: Build 237 at `55afaa689603263c1ad415436e90cce6679808c3`
- Owner: IHOS release engineering
- Status: Monitored exception; current execution path not applicable
- Approval gate: human approval before a React Router major-version upgrade

## Authoritative finding

GitHub classifies the advisory as high severity for `react-router` versions
`>=7.12.0 <8.3.0`, with 8.3.0 listed as patched. The advisory explicitly
states that applications are affected only when they use React Router's
unstable React Server Components APIs.

The Version 1.0 lockfile currently resolves `react-router` and
`react-router-dom` to 7.18.1. `npm audit --omit=dev` therefore reports the
advisory and does not offer an automatic compatible fix.

## IHOS applicability evidence

Iron House OS is a client-rendered Vite single-page application:

- Vite uses only `@vitejs/plugin-react`.
- The application mounts with React DOM and `BrowserRouter`.
- Application routes use declarative browser APIs from `react-router-dom`.
- No React Router framework server, server action, RSC router, RSC Vite plugin,
  RSC adapter, or React server-function directive is configured.
- FastAPI is the independent backend; it does not execute React Router server
  actions.

The vulnerable unstable RSC request/action path is therefore not present in
the reviewed candidate. This is an applicability determination, not a claim
that the locked package version falls outside the advisory's reported range.

## Enforced control

`scripts/check_react_router_rsc_boundary.py` runs in both CI and Release
Readiness. It fails closed if a known RSC package, Vite plugin, router API,
server-request API, or server-function directive is added to the frontend.
The script and this record are integrity-bound into the release evidence
manifest.

Issue #94 remains the monitoring record. A future move to React Router 8.3.0
or later requires a separately reviewed compatibility change and complete
frontend, browser, mobile, accessibility, staging, backup/restore, and
rollback gates before merge or deployment.
