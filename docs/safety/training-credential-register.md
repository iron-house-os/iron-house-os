# Safety training and credential register

This increment advances issue #70 Phase 3 by replacing the browser-local People & Compliance credential list with company records already stored in `employee_certifications`.

## Controls

- Only administrators and operations managers can add credential records or export the company register.
- Portal roles continue to receive only the certification records allowed by the existing field-operations bootstrap authorization; the company-wide export is management-only.
- Expiry status is calculated from the stored expiry date: `current`, `expires_soon` (60 days or fewer), `expired`, or `no_expiry`.
- Management alerts continue to identify credentials expiring within 60 days.
- The CSV export neutralizes spreadsheet-formula prefixes in user-entered text and is delivered as `safety-credential-status.csv`.

## Deliberate boundary

The register reports operational dates and stored evidence only. It does not decide whether a worker is legally compliant, competent, or authorized for a task. Required-credential policy, regulatory conclusions, disciplinary records, and external reporting remain behind the human approval gate in issue #70.

The company safety manual, worker orientations, supervisor verification, and field controls remain the authoritative operational sources. A credential status cannot release blocked work.

## Validation

Backend tests verify:

- viewer denial for credential creation and company CSV export;
- operations-manager creation;
- 60-day status calculation;
- CSV response headers and exported status evidence.

Frontend validation covers the existing locked Iron House design while replacing the local credential state with the authenticated field-operations API.
