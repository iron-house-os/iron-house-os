# Data recovery

1. Isolate the affected deployment and preserve logs and damaged storage for analysis.
2. Inventory backup bundles newest-first. Run `scripts/restore_production.sh --verify-only <bundle>` before choosing a recovery point.
3. Confirm the manifest, checksums, database dump, upload archive, release identifier, and schema revision. Reject incomplete or corrupt bundles.
4. Restore into a disposable environment first. Verify database connectivity, current migrations, user login, representative records, and uploaded-file checksum/download.
5. Record the expected data-loss window between the recovery point and incident time.
6. With operator approval, restore the verified bundle to the isolated target using the documented restore command.
7. Require `/health`, `/readiness`, authenticated release smoke, and a fresh post-recovery backup before reopening access.

For S3-compatible storage, bucket version recovery is performed through the storage provider’s approved operator tooling. The application never makes buckets public and never deletes object versions during this procedure.
