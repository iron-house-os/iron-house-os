# Security Hardening Checklist

IHOS must remain internal-only until these controls are complete.

## Authentication

- Add authenticated login.
- Disable anonymous project access.
- Protect API routes.
- Add session timeout.

## Authorization

- Define owner/admin/estimator/viewer roles.
- Restrict project delete/archive.
- Restrict supplier contact edits.
- Restrict final bid export.

## Files

- Scan uploads where possible.
- Restrict file types.
- Store files outside the web root.
- Use signed URLs for downloads.

## Audit

- Log project changes.
- Log estimate changes.
- Log RFQ sends.
- Log final bid exports.

## Deployment

- Use HTTPS.
- Keep secrets out of Git.
- Use managed database backups.
- Restrict admin panels by IP or VPN.
