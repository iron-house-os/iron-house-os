# Build 235 — Canonical Identity Deployment Preflight

## Task card

- **Lead function:** System Governance
- **Supporting functions:** Quality Assurance, Administration and Communications
- **Owner:** Jeremie Peters
- **Priority:** High
- **Status:** Ready
- **Environment:** Development only
- **Approval gate:** Pull-request review and green release gates before merge or deployment

## Objective

Prevent a production cutover from taking Iron House OS offline when the protected
bootstrap administrator email still uses a retired or malformed company domain.

## Verified

- Build 231 rejects a retired bootstrap administrator email when the backend starts.
- Production recovery on 2026-07-24 confirmed that a retired-domain value caused the
  backend container to exit, prevented the frontend from starting and produced HTTP 502.
- The canonical company identity domain is `ironhousecontracting.com`.
- The production web hostname remains `os.ironhousecivil.com`.

## Delivered

- A fail-closed cutover preflight validates the bootstrap administrator email before
  Nginx enters maintenance mode or Docker Compose changes the application stack.
- The check rejects missing local parts, missing `@` separators and every
  non-canonical domain.
- Domain comparison is case-insensitive.
- A regression test protects both the canonical-domain contract and the required
  ordering ahead of the maintenance gateway change.

## Risks and controls

- **Risk:** A future identity-domain change could require a coordinated update.
  **Control:** Change the canonical-domain contract only through an approved release
  with production environment and migration evidence.
- **Risk:** A malformed protected environment could interrupt deployment.
  **Control:** The preflight exits before user traffic or running containers are
  changed.

## Record

The pull request and release-gate results are the Build 235 system of record. Production
deployment remains separately controlled.
