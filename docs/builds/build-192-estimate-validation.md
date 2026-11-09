# Build 192 — Estimate Validation Engine

Status: implemented; pending CI validation.

Build 192 adds a deterministic estimate quality gate before pricing review or bid-package generation.

## Implemented controls
- Reject empty estimates.
- Require resolvable civil cost codes when configured.
- Suggest cost codes from line-item descriptions.
- Reject unpriced line items when configured.
- Warn on zero quantities.
- Warn when profit markup is below the configured minimum.
- Warn when assumptions or exclusions are missing.
- Return structured error and warning counts through `POST /api/v1/estimates/validate`.

Build 193 remains locked until this branch and the exact merged-main baseline are green.
