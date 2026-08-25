# Production deployment agent

The production deployment agent removes routine command entry from the
DigitalOcean web console.

## Control boundary

- The runner is registered only to `iron-house-os/iron-house-os`.
- Production jobs require the `ihos-production` runner label.
- The workflow accepts an exact 40-character release SHA and a successful
  Release readiness run ID.
- The deployment wrapper rejects the wrong host, repository, SHA, dirty
  checkout, missing evidence, and commits not present on `origin/main`.
- The wrapper discovers and pins the running production Docker Compose project
  name before cutover, preventing a parallel stack from being created.
- After the pre-cutover backup and maintenance gate, the cutover performs a
  clean recreation of that pinned Compose project. It removes service containers
  and orphans without removing named volumes, retries transient stale-container
  cleanup once, and then fails closed with Compose diagnostics.
- Scheduled backups remain nonblocking by default. Both mandatory cutover
  recovery backups wait for an overlapping backup, with a five-minute maximum;
  timeout remains a deployment failure before or after cutover.
- The runner account has passwordless sudo access only to the validated
  production deployment wrapper.
- Before cutover, the workflow verifies that the installed wrapper is owned by
  `root:root`, has mode `0755`, and exactly matches the trusted workflow
  checkout. A stale or modified wrapper fails closed.
- The production workflow uses GitHub's `production` environment as the human
  approval boundary.

## One-time bootstrap

Run the installer once on `iron-house-os-prod-1` from an approved `main`
checkout:

```bash
sudo bash ops/digitalocean/install-production-runner.sh
```

After the service reports healthy, production releases are started through the
manual `Production deploy` GitHub Actions workflow. Do not run arbitrary shell
commands through the production runner.

## Controlled wrapper refresh

Whenever `ops/digitalocean/production-deploy-wrapper.sh` changes, refresh only
the root-owned launcher from an approved `main` checkout on
`iron-house-os-prod-1` before the next deployment:

```bash
sudo bash ops/digitalocean/install-production-runner.sh --refresh-wrapper-only
```

This mode updates `/usr/local/sbin/ihos-production-deploy`, rewrites and
validates its narrow sudoers rule, and exits without registering, restarting,
or reconfiguring the runner service. Treat the refresh as a production
infrastructure change: obtain explicit approval and record the exact source
commit before running it.

## Protected business-import launcher

Approved production cutovers also install
`/usr/local/sbin/ihos-production-business-import` as `root:root 0755` and a dedicated,
validated sudoers rule for `ihos-runner`. The launcher is intentionally separate from the
deployment launcher. It accepts only an exact deployed main SHA, a direct JSON child of
`ops/production-business-imports/`, and an evidence path inside the restricted runner temporary
directory. It verifies live readiness reports the same release SHA before sourcing the protected
environment and passes only IHOS port plus bootstrap credentials to the importer.

Do not grant the runner read access to `/etc/iron-house-os/production.env` and do not add generic
sudo, shell, Docker, or file-copy privileges. Production imports remain manual and require a second
protected `production` environment approval after the release deployment.

