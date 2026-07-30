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
- The runner account has passwordless sudo access only to the validated
  production deployment wrapper.
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
