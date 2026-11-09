# Issue 159 — Backups management routing validation

Date: 2026-08-06  
Branch: `agent/build/159-job-63ee7f2a`  
Pull request: draft PR #160

## Focused control review

- **Authorization:** authenticated submitters retain create/own-read access; destination mutation and Finance review queries require `admin` or `operations_manager`. Viewer denial is covered at both endpoints.
- **Isolation and media:** Finance queues return only management-authorized intake metadata and reuse the existing private media content URL. No original, hash, uploader, or media authorization field is changed.
- **Audit:** each actual destination change records the management actor, event timestamp, previous destination, and new destination. Re-selecting the current destination is a no-op and creates no duplicate event.
- **Concurrency/idempotency:** routing uses one destination column and an atomic compare-and-set on the previous destination. A stale competing route returns HTTP 409; an identical retry returns the persisted item.
- **Finance gates:** analysis and routing no longer create receipt or document records. No approval, posting, export, reconciliation, payment, packing-slip acceptance, project cost, quantity, or quality field is mutated.

## Executed evidence

- Focused backend: `25 passed in 7.02s` for `tests/backend/test_backups.py`.
- Focused frontend: `2 passed` files / `6 passed` tests for Backups and Financial Control queues.
- Migration drill on disposable SQLite: upgrade to head, downgrade to `20260805_0015`, re-upgrade; final revision `20260806_0016 (head)`.
- Complete backend: `ruff check .` passed; `289 passed, 1 warning in 117.22s`.
- Complete frontend: visual design lock passed for 13 protected files; React Router RSC boundary passed with 114 files scanned and no errors; TypeScript lint passed; `22 passed` files / `63 passed` tests; production build completed with 1,865 modules transformed.
- Playwright discovery: three focused projects listed—desktop Chromium, Pixel 7/mobile Chromium, and iPad Pro 11/WebKit—with Axe accessibility checks on Backups and Finance queue screens.
- Staging wrapper shell syntax and production-environment rejection passed.

## Environment-limited gates

This worker has no Docker CLI and lacks Playwright native GTK/WebKit libraries. The focused browser run was attempted but all three projects stopped before test code at browser launch (`libatk-1.0.so.0` and related host libraries missing). Disposable staging smoke, backup/restore, and rollback could not run locally because Docker is absent. These remain mandatory draft-PR Release readiness checks; no production or shared staging environment was touched.

## Rollback

Revert the application commit first. In a disposable or explicitly approved non-production database, `alembic downgrade 20260805_0015` removes only the new review-destination column/index and preserves Backups originals, uploader identity, intakes, legacy route records, and audit events. Production rollback or deployment requires separate owner approval.
