# Fernie 2026 historical staging intake

Issue: #132

The City of Fernie 2026 Sanitary Manhole Infiltration Repair tender closed on 2026-08-14 at 14:00 MT. The package may be imported into IHOS staging as a historical opportunity, but it must not be represented as an active bid and the submission outcome must remain **unverified** until owner evidence establishes otherwise.

## Dependency

PR #201 (issue #129 Drive tender importer) must be merged before this intake.

## Dry run

```bash
python -m app.tools.fernie_staging_import --operator "Staging Operator"
```

The dry run creates no records. Review the generic Drive-import duplicate decisions and the planned project, tender, RFQ package, bid workspace, and document links.

## Controlled staging apply

A staging mutation requires explicit owner approval. The command rejects production and requires acknowledgement of the expired closing date:

```bash
ENVIRONMENT=staging python -m app.tools.fernie_staging_import \
  --operator "Staging Operator" \
  --apply \
  --confirm-expired-intake
```

The import is atomic and idempotent. It records:

- one historical opportunity project;
- one tender in `reviewing` status with submission status `unverified`;
- one draft RFQ package;
- one draft bid workspace for CAD 169,500;
- the 11-manhole scope and all listed provisional allowances;
- immutable links to the RFP, proposal, estimate, and inspection videos.

## Verification

After an approved staging apply, record all object IDs, linked-document counts, a second idempotency run, API/UI smoke results, and any unresolved duplicate decision. Do not alter production.
