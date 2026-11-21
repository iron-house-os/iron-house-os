# Release rollback

1. Freeze writes and record the current release identifier, database revision, incident time, and last known-good release.
2. Take and verify a fresh backup when the database and object store are readable. Never overwrite the last verified recovery point.
3. Review the target release migration notes. Do not run a destructive downgrade unless its data-loss behavior has been reviewed and accepted.
4. Select a security-preserving rollback release. For the November 2026 NGINX repair, use the merged commit of PR #431 as the earliest rollback target. It retains the application code from `699363c421c652f7019024d90e01f14406de9efa` with the NGINX repair. An older application version requires a reviewed backport of the pinned image, host update, HTTP/2 mitigation, and recovery changes with fresh Release Readiness evidence. Record the exact approved target SHA, then redeploy its immutable image and matching configuration. Keep secrets out of shell history and evidence files.
5. If schema compatibility prevents startup, restore the verified pre-release backup using the recovery runbook instead of improvising SQL changes.
6. Require green `/health`, `/readiness`, authenticated smoke, document download, and a representative write before reopening access.
7. Record the final image digest, schema revision, verification evidence, and operator acceptance.

Rollback does not provision infrastructure or notify external parties.

The Ubuntu host NGINX security update stays installed during application rollback.
The cutover verifies the Ubuntu package revision and restarts NGINX before opening
the replacement application. Failed cutover recovery uses the mitigated gateway
after application readiness, or the maintenance gateway while the application is
unavailable. Re-enabling HTTP/2 requires a separate configuration change after the
host security update is verified.
