# Administrator Access Recovery Runbook

Use this runbook only when the canonical IHOS administrator cannot sign in and normal
in-app administrator recovery is unavailable.

## Preconditions

Do not perform recovery until:

1. Builds 231 and 232 are approved and deployed through the protected release process.
2. A complete recovery backup has been created and verified.
3. The maintenance window and recovery operator are approved.
4. The Build 231 identity migration has been applied or its dry run has been reviewed.
5. The operator is connected to the canonical production server,
   `iron-house-os-prod-1`.

Never place the temporary password in a command argument, chat, shell history, evidence
file or support ticket.

## Inspect the Account

This command is read-only:

```bash
sudo docker compose \
  --env-file /etc/iron-house-os/production.env \
  -f docker-compose.production.yml \
  run --rm --no-deps backend \
  python -m app.tools.admin_access_recovery inspect \
  --email jeremie@ironhousecontracting.com
```

Confirm:

- the display name is Jeremie Peters;
- the role is `admin`;
- the account is active;
- `eligible` is `true`;
- the account UUID matches the approved recovery target.

## Recover Access

Run interactively so the password prompts remain hidden:

```bash
sudo docker compose \
  --env-file /etc/iron-house-os/production.env \
  -f docker-compose.production.yml \
  run --rm --no-deps backend \
  python -m app.tools.admin_access_recovery recover \
  --email jeremie@ironhousecontracting.com \
  --confirm-account-id <UUID-FROM-INSPECTION> \
  --reason "Business account migration access recovery" \
  --operator "Jeremie Peters" \
  --apply
```

Enter the temporary password twice at the hidden prompts. Save the resulting JSON as
restricted recovery evidence only after confirming it contains no password or password
hash.

The recovery:

- preserves the account ID, email, role and active state;
- replaces the password hash;
- increments the session version and invalidates existing sessions;
- clears the account login throttle;
- requires a password change after the next successful login.

## Complete the Recovery

1. Sign in at `https://os.ironhousecivil.com` using the canonical email and temporary
   password.
2. Complete the forced password change.
3. Confirm administrator access and required navigation.
4. Do not reuse or retain the temporary password.

## Verify Cutover

```bash
sudo docker compose \
  --env-file /etc/iron-house-os/production.env \
  -f docker-compose.production.yml \
  run --rm --no-deps -T backend \
  python -m app.tools.admin_access_recovery verify-cutover \
  --email jeremie@ironhousecontracting.com
```

The result is ready only when:

- no active identity or routing values remain for Build 231 migration;
- the configured bootstrap email matches the canonical administrator;
- the administrator exists, is active and has the admin role;
- the forced password change is complete.

## Stop Conditions

Stop without applying recovery if:

- inspection reports more than one matching account;
- the account ID, display name, domain, role or active state is unexpected;
- the recovery backup is missing or unverified;
- the reason or operator is not approved;
- any command output contains a password or password hash.

## Rollback

If the confirmed account was changed incorrectly, stop the application and restore the
verified pre-recovery backup using the approved recovery procedure. Do not create a
replacement administrator, merge accounts or edit password hashes directly.
