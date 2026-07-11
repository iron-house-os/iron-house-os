# Build 194 — Quantity Takeoff Normalization

Build 194 adds a deterministic normalization gate between drawing takeoff and estimating.

## Delivered

- Duplicate detection by cost code/description, category, unit, and revision
- Optional duplicate quantity consolidation
- Drawing-reference requirements
- Configurable minimum-confidence threshold
- Zero-quantity rejection
- Revision boundaries that prevent obsolete/current quantities from being combined
- Estimate-ready handoff items
- Audit warnings and rejected-item reporting
- `POST /api/v1/takeoff/normalize`

## Boundary

This build normalizes structured takeoff data. Direct PDF geometry recognition and autonomous drawing measurement remain separate drawing-processing work.

## Validation gate

Backend install, Ruff, pytest, frontend install, lint, tests, and production build must pass before merge. The exact merged `main` baseline must then pass separately before Build 195 begins.
