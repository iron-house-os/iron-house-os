# Release rollback

1. Freeze writes and record the current release identifier, database revision, incident time, and last known-good release.
2. Take and verify a fresh backup when the database and object store are readable. Never overwrite the last verified recovery point.
3. Review the target release migration notes. Do not run a destructive downgrade unless its data-loss behavior has been reviewed and accepted.
4. Redeploy the last known-good immutable image and its matching configuration. Keep secrets out of shell history and evidence files.
5. If schema compatibility prevents startup, restore the verified pre-release backup using the recovery runbook instead of improvising SQL changes.
6. Require green `/health`, `/readiness`, authenticated smoke, document download, and a representative write before reopening access.
7. Record the final image digest, schema revision, verification evidence, and operator acceptance.

Rollback does not provision infrastructure or notify external parties.
