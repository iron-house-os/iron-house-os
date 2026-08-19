# Google Drive tender metadata import

Issue: #129

This controlled admin command imports non-secret metadata and links from the current `Iron House OS/01_Tenders` Drive folder into IHOS project and document records. It never downloads or modifies Drive source files.

## Safety boundaries

- Dry-run is the default.
- `--apply` is rejected unless `ENVIRONMENT=staging`.
- The checked-in manifest contains Drive IDs, metadata, and URLs only; it contains no credentials.
- The command uses an exclusive lock and a single database transaction.
- The importer is idempotent: stable Drive folder and file IDs update existing records instead of duplicating them.
- Ambiguous project matches and cross-project file conflicts are reported and skipped.
- Production apply is intentionally unsupported.

## Dry run

From the backend environment:

```bash
python -m app.tools.drive_tender_import --operator "Staging Operator"
```

Review the JSON report before any apply. Confirm create/update counts, consolidated aliases, unresolved folders, and document conflicts.

## Staging apply

A staging mutation requires explicit owner approval and staging credentials:

```bash
ENVIRONMENT=staging python -m app.tools.drive_tender_import --operator "Staging Operator" --apply
```

After apply, run the command again in dry-run mode. All previously created projects and linked documents should report as updates, with no duplicate active project or document.

## Manifest refresh

The manifest is a point-in-time metadata snapshot generated from the connected Drive folder. Refresh it before staging apply when the source folder contents change. Preserve source Drive IDs and URLs, keep the original Drive objects immutable, and never commit provider credentials.

## Verification evidence

Record:

- source manifest revision and generation time;
- dry-run create/update/consolidate/ambiguous counts;
- staging project IDs and linked document counts;
- a second idempotency run;
- project/document UI smoke results;
- unresolved duplicate decisions.

No production deployment or production data mutation is part of this workflow.
