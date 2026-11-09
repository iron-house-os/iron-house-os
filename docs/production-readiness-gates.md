# Production Readiness Gates

IHOS should not be exposed outside Iron House until these gates are met.

## Gate 1: Internal local use

- Local launch works.
- Smoke check passes.
- One project can be created.
- One takeoff can be saved.
- One estimate workspace can be saved.
- Project readiness reflects saved records.

## Gate 2: Private hosted use

- HTTPS configured.
- Database backups configured.
- Secrets are managed outside Git.
- Upload storage is private.
- Admin access is restricted.

## Gate 3: Company-wide internal use

- Authentication enabled.
- User roles defined.
- Audit logging enabled.
- Error monitoring enabled.
- File retention policy defined.

## Gate 4: Supplier-facing use

- RFQ recipient permissions verified.
- Supplier links are tokenized and expiring.
- Download links are signed.
- Email send audit logs exist.
- Legal/privacy footer is reviewed.
