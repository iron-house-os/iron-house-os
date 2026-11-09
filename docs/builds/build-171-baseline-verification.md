# Build 171 — Post-Build-170 Baseline Verification

## Objective
Establish the exact production-readiness baseline before deployment and identity work begins.

## Locked baseline
- Repository: `iron-house-os/iron-house-os`
- Branch: `main`
- Baseline commit: `31b858c3afc59ff8c59303e021be4f4460c376b3`
- Prior completed range: Builds 1–170

## Required gate
The Build 171–180 branch must not merge unless the existing backend and frontend CI workflows pass against the complete branch.

## Verification scope
- Backend dependency installation
- Ruff linting
- Pytest suite
- Frontend dependency installation
- Frontend linting
- Frontend tests
- Frontend production build
- Database migration integrity
- Deployment configuration review

## Result
The Build 170 baseline is recorded and the next production-readiness block is authorized to proceed on `build/build-171-to-180-gated`.
