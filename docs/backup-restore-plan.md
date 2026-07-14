# Backup and Restore Plan

## Backup targets

- PostgreSQL database.
- Uploaded project files, audit records, and generated artifacts in `/app/data`.
- Environment configuration is deliberately excluded and must be protected separately.

## Backup frequency

- Development: manual before major schema changes.
- Internal production: daily minimum.
- Active bid week: before and after each major estimate revision.

## Restore test

1. Create a bundle with `scripts/backup.sh --output DIRECTORY`.
2. Verify and restore it with `scripts/restore.sh --backup DIRECTORY --confirm-restore`.
3. Confirm the authenticated smoke check passes.
4. Open a known project and verify a stored document checksum.

The release-readiness workflow performs this drill against a disposable production stack on every recovery-path change.

## Rule

A backup that has not been restore-tested is not trusted.
