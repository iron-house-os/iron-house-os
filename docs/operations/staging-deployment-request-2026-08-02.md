# IHOS staging deployment request — August 2, 2026

## Authorized target

- Host: `staging.os.ironhousecivil.com`
- Droplet: `iron-house-os-build-222-agent`
- Droplet ID: `587178575`
- Public IP: `165.245.236.128`
- Release commit: `bd8af914245ce5fb141abcc697dcd9081ab2c084`
- Environment: staging only

## Required action

On the existing staging host, update the checkout to the exact release commit and use the repository's fail-closed staging operator:

```bash
sudo bash ops/digitalocean/staging-deploy.sh \
  --prepare \
  --host staging.os.ironhousecivil.com \
  --release bd8af914245ce5fb141abcc697dcd9081ab2c084
```

If HTTPS is already configured and the existing certificate remains valid, run the finalizer for the same exact release:

```bash
sudo bash ops/digitalocean/staging-deploy.sh \
  --finalize-https \
  --host staging.os.ironhousecivil.com \
  --release bd8af914245ce5fb141abcc697dcd9081ab2c084
```

Do not use production compose files, production environment files, production nginx configuration, or the production host.

## Acceptance evidence

Record:

- deployed Git commit
- staging Compose project and container health
- HTTPS status
- authenticated login and role-denial smoke
- projects/estimating/RFQ/documents smoke
- FLHA smoke
- foreman time-sheet smoke
- receipt/media smoke
- rollback reference

Open a minimal repair PR only for reproducible Critical or High application defects. Do not add features or redesigns.
