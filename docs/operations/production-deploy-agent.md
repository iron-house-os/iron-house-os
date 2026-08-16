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
