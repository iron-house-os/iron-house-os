# Production business-record import

This is the supported no-browser path for a small, owner-approved intake of IHOS projects,
customer quotes and customer invoices.

## Controls

- Work starts from a linked issue and a draft pull request.
- Pull requests run the disposable validation suite only; they cannot reach production.
- Production import is manual-only and requires the exact SHA already deployed to production.
- The protected `production` environment job cannot continue until the configured reviewer approves it.
- A root-owned launcher verifies the deployed release, approved bundle, live readiness identity,
  evidence destination and least-privilege environment before calling the IHOS loopback API.
- The runner cannot read `production.env`; only the narrow launcher can source the three values
  required for authenticated import.
- Projects enter as `opportunity`; no project/job number is allocated.
- Customer quotes and invoices use the API's `draft` defaults. The importer cannot issue,
  approve, accept or award them.
- Stable import keys, external references and invoice numbers make repeat runs idempotent.
- A conflicting pre-existing record fails closed for manual review instead of overwriting data.
- Every production run writes verification evidence to the linked issue and a 90-day artifact.

## Bundle workflow

1. Add exactly one reviewed JSON bundle under `ops/production-business-imports/`.
2. Run `python3 -m unittest discover -s ops/scripts/tests -p 'test_*.py' -v`.
3. Run `python3 ops/scripts/production_business_import.py validate --input <bundle>`.
4. Open an issue-linked draft pull request and complete normal review/CI.
5. Merge only with owner authorization, complete Release Readiness, and deploy that exact SHA
   through the normal protected production deployment workflow.
6. Dispatch `Validate and import approved business records` with that deployed SHA and the exact
   bundle path.
7. Approve the protected production import after checking the bundle totals, customer identity,
   deployed release SHA and draft-only state.

Rollback is intentionally manual: records are never deleted automatically. If a created draft is
wrong, void/archive it through the normal IHOS authorization workflow and retain the import evidence.
