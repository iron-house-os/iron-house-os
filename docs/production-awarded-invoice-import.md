# Production awarded-job invoice import

This is the supported no-browser path for one owner-approved historical awarded project and its
draft customer invoice.

## Controls

- Work starts from a linked issue and draft pull request.
- Pull requests run disposable validation only and cannot reach production.
- Merging a bundle never starts a production import.
- Production import is manual-only and requires the exact SHA already deployed to production.
- The protected `production` environment requires its configured human reviewer.
- A root-owned launcher verifies the immutable deployed release, approved bundle path, live
  readiness release identity, repository origin and runner-temporary evidence destination.
- The restricted runner cannot read `production.env`; only the launcher sources the IHOS port
  and bootstrap credentials required for authenticated loopback API calls.
- IHOS generates the awarded project's permanent job number. The bundle cannot supply one, and
  the importer rejects generated job numbers containing hyphens.
- The customer invoice remains `draft`; the importer cannot approve, issue or pay it.
- Stable import keys and invoice numbers make retries idempotent. Identity conflicts fail closed.
- Verified evidence is attached to the linked issue and retained as a 90-day workflow artifact.

## Approval sequence

1. Review the exact project, billing identity, invoice lines, totals, GST, dates and terms in the
   issue-linked bundle.
2. Complete normal draft-PR review, CI and Release Readiness.
3. Merge only with owner authorization.
4. Deploy that exact main SHA through the protected production deployment workflow. This is the
   first protected approval and installs the matching restricted launcher.
5. Dispatch `Validate and import approved awarded job invoice` with:
   - the exact deployed 40-character release SHA; and
   - the exact bundle path under `ops/production-awarded-invoice-imports/`.
6. At the second protected approval, recheck the SHA and exact record scope before approving.
7. Verify the issue evidence, generated no-hyphen job number, awarded project, draft invoice,
   exact totals and public production release identity.

Never rerun a failed pre-hardening push-triggered workflow. It was not bound to a deployed release
and could not read the protected environment.

Rollback is intentionally manual. Imported records are never deleted automatically. Correct a
wrong project or invoice through normal IHOS archive/void controls and retain the evidence trail.
