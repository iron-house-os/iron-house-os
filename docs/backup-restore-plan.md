# Backup and Restore Plan

## Backup targets

- PostgreSQL database.
- Uploaded project files.
- Environment configuration.
- Generated estimate workbooks and bid packages, if stored.

## Backup frequency

- Development: manual before major schema changes.
- Internal production: daily minimum.
- Active bid week: before and after each major estimate revision.

## Restore test

1. Restore database to a clean environment.
2. Restore file storage.
3. Start backend and frontend.
4. Run smoke check.
5. Open a known project.
6. Confirm takeoffs, estimates, RFQs, and documents are present.

## Rule

A backup that has not been restore-tested is not trusted.
