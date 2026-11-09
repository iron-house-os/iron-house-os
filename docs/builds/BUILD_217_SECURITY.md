# Build 217 security notes

- Invitation tokens are random and only SHA-256 hashes are stored.
- Tokens expire and can be revoked or replaced.
- Employee activation requires a separate administrator approval step.
- Public portal routes are limited to token-scoped onboarding access.
- Sensitive payroll, banking, tax, identity, and emergency-contact fields must not be included in invitation email content or audit metadata.
- Production release requires staging verification of permissions, email configuration, and privacy controls.
