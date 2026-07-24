# Email Identity Domain Migration Runbook

This runbook changes current operational email identities to
`ironhousecontracting.com`. It does not change `os.ironhousecivil.com`.

## Approval and Preconditions

Do not run `--apply` until all of the following are verified:

1. The release containing Build 231 has passed CI and has been separately approved for
   production deployment.
2. A complete recovery backup has been created and verified.
3. `/etc/iron-house-os/production.env` has the canonical
   `BOOTSTRAP_ADMIN_EMAIL`.
4. The dry-run JSON has been reviewed and contains no collision.
5. The production apply has explicit approval from Jeremie Peters.

## Backup

From the production repository:

```bash
sudo IHOS_COMPOSE_ENV_FILE=/etc/iron-house-os/production.env \
  bash scripts/backup.sh \
  --output /var/backups/iron-house-os/pre-email-domain-migration-20260724
```

## Dry Run

The default command is read-only:

```bash
sudo docker compose \
  --env-file /etc/iron-house-os/production.env \
  -f docker-compose.production.yml \
  run --rm --no-deps -T backend \
  python -m app.tools.migrate_email_domain \
  | sudo tee /var/lib/iron-house-os/email-domain-dry-run-20260724.json
```

Review `change_count`, `changes_by_area`, every proposed replacement and the protected
history policy. A collision exits with status 2 and performs no write.

## Apply

Only after the approval gate:

```bash
sudo docker compose \
  --env-file /etc/iron-house-os/production.env \
  -f docker-compose.production.yml \
  run --rm --no-deps -T backend \
  python -m app.tools.migrate_email_domain \
  --apply \
  --confirm ironhousecontracting.com \
  | sudo tee /var/lib/iron-house-os/email-domain-apply-20260724.json
```

The apply is transactional and idempotent. Migrated accounts keep their passwords,
roles and IDs, but their existing sessions are invalidated.

## Verification

1. Run the dry-run command again and confirm `change_count` is `0`.
2. Sign in with the canonical administrator email and the existing password.
3. Confirm the administrator role and required menus.
4. Confirm employee and supplier email displays.
5. Preview an RFQ communication workflow and confirm canonical sender/recipient routing.
6. Confirm production readiness is healthy.
7. Retain backup, dry-run and apply evidence with the Build 231 approval record.

## Rollback

Stop the application and restore the verified pre-change recovery backup using the
approved recovery procedure. Do not manually merge colliding accounts or rewrite
historic audit records.
