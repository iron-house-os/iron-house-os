# Build 216 — Approved live infrastructure cutover

## Approved target

Jeremie approved Build 216 on 2026-07-15 with a CAD 60 monthly ceiling:

- DigitalOcean Basic Droplet, Toronto (`tor1`), 2 vCPU and 4 GiB RAM
- `os.ironhousecivil.com`
- Nginx TLS termination with Let's Encrypt
- private, encrypted, versioned AWS S3 storage in `ca-central-1`
- daily Droplet backups plus verified off-host recovery bundles
- five-minute external health and readiness monitoring
- 2026-07-19 13:00–15:00 UTC maintenance window
- Jeremie as operator/approver and Mac as rollback owner

## Delivered controls

- the application port now binds only to loopback
- cloud-init prepares a firewalled Ubuntu Docker host without embedding secrets
- maintenance and live Nginx configurations keep the public route fail-closed
- cutover requires an exact 40-character commit, a clean tree, a checksum-valid release evidence artifact with all four required gates passed, protected secrets, matching DNS, private/versioned/encrypted S3 targets, full authenticated smoke, pre/post backups, and explicit `--confirm-go`
- failed public verification restores the maintenance response
- scheduled recovery bundles are archived to S3 and verified by SHA-256 metadata
- operator acceptance is written on the host only after the public HTTPS smoke and post-cutover backup succeed

## External boundary

Repository validation cannot create a DigitalOcean account, charge a payment method, create an AWS bucket, edit the existing domain's DNS, or register UptimeRobot recipients. Those provider actions require authenticated provider access. The cutover script refuses to continue until those approved resources and protected credentials exist.
