# Authentication Plan

## MVP private phase

- Keep deployment private.
- Restrict network access where possible.
- Use a single admin/operator if necessary.

## Internal company phase

- Add login.
- Add estimator/admin roles.
- Protect all API routes except `/health` and `/readiness`.
- Record user ID on project, estimate, takeoff, RFQ, and document changes.

## Supplier-facing phase

- Do not use normal user accounts for suppliers.
- Use expiring token links for RFQ package access.
- Restrict each supplier token to its own package.
- Log all downloads and quote uploads.
