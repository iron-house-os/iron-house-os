# Build 180 — Staging Validation Gate

## Completed build controls
- Build 171: locked and recorded the post-Build-170 baseline.
- Build 172: added the production environment contract.
- Build 173: defined production authentication requirements.
- Build 174: defined organization tenancy and user roles.
- Build 175: defined frontend permission enforcement.
- Build 176: defined the production migration gate.
- Build 177: defined the Iron House production seed manifest.
- Build 178: defined the staging deployment blueprint.
- Build 179: added an executable staging smoke-test runner.

## Merge gate
This block is not considered production validated until all of the following are true:

- [ ] Backend CI is green.
- [ ] Frontend CI is green.
- [ ] Database migrations pass against empty and upgraded PostgreSQL databases.
- [ ] A staging frontend URL is recorded.
- [ ] A staging API URL is recorded.
- [ ] The deployed commit SHA is recorded.
- [ ] `scripts/staging-smoke-test.sh` passes.
- [ ] Bootstrap credentials are replaced.
- [ ] Authentication and tenant-isolation tests pass.

## Current boundary
Builds 171–180 establish the production-readiness contract and deployment gate. The next implementation block must satisfy the authentication, tenancy, deployment and smoke-test requirements before the application is described as production-ready.

Build 181 remains locked until this branch passes repository CI and the merge gate is reviewed.
