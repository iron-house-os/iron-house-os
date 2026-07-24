# Identity governance monitoring

This development runbook defines the proposed weekly identity-health check. It does not authorize a production installation.

## Command

Run from the application release directory with the application environment loaded:

```bash
python scripts/identity_governance_report.py \
  --output /var/lib/iron-house-os/evidence/identity-governance.json \
  --fail-on critical
```

The command:

- reads account governance fields without changing them;
- writes a versioned JSON evidence envelope atomically;
- includes a SHA-256 digest of the snapshot;
- excludes password hashes and session versions;
- exits `3` when a finding meets the selected alert threshold.

## Proposed schedule

- Frequency: weekly, Monday morning.
- Owner: named Iron House OS administrator.
- Alert threshold: critical until management approves the formal access policy.
- Retention: pending management and legal approval.
- Notification channel: pending administrator recipient and channel approval.

## Response

1. Preserve the evidence file and command result.
2. Inspect the Identity Governance Centre.
3. Confirm each affected named account with management.
4. Use the approved recovery or deactivation procedure.
5. Do not delete or merge duplicate identities until the records are reconciled.
