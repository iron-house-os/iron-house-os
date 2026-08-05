# Backups photo inbox

Issue: #154. Backups is a single-photo, review-only document intake path. It reuses the private media store and does not approve, post, pay, reconcile, or accept any routed record.

## Data flow

1. An authenticated user uploads exactly one image to the existing media API with category `backup`.
2. `POST /api/v1/backups` binds that immutable original media ID and SHA-256 hash to one intake and records the uploader's identity and portal role.
3. The daily controller atomically claims each pending intake once and reads the original media version.
4. Local OCR runs before classification. Banking, payroll, SIN, medical, or valid full-card content is quarantined without an external request.
5. When configured and permitted, the OpenAI Responses API receives only screened OCR text, uses a strict four-label schema, and has `store` disabled. Local heuristics are the offline/failure fallback.
6. A receipt becomes an unapproved `needs_review` receipt. A supplier invoice or packing slip becomes a registered document whose workflow metadata is `needs_review`. Other and low-confidence items stay in Backups triage.

The intake status is one of `pending`, `processing`, `routed`, `needs_review`, or `failed`. Audit events record submission, claim, routing/triage/failure, and retry. The route ledger's unique media-hash/type key plus unique intake media ID prevents duplicate intake or destination records across retries.

## Authorization

- Every authenticated administrator, management user, estimator, employee, foreman, and operator can submit.
- Non-management users can list/read only their own intake records and original images.
- Management and administrators can view the company queue, run the controller, and retry failed or triage records.
- Existing project, document, receipt, and private-media authorization continues to govern destination access.

## Controller entry points

The authenticated management endpoint is:

```text
POST /api/v1/backups/controller/daily?limit=100
```

For an unattended scheduler in an approved staging/production environment, use the application process entry point rather than a browser session:

```bash
cd backend
python -m app.tools.process_backups
```

The command uses the configured application database, private media provider, local OCR dependencies, and optional OpenAI API configuration. Configure scheduling and credentials through the existing environment management process; do not place credentials in the command or repository.

## Staging acceptance

Run these only against an approved staging environment:

1. Sign in once as a field user and once as management.
2. On phone, iPad/WebKit, and desktop, submit one image with a note and project hint. Confirm the same media ID and immutable-original hash persist after reload.
3. Confirm the submitter can access their intake and original while an unrelated submitter cannot; confirm management can access the company queue.
4. Run one controller pass and verify its audit event sequence.
5. Exercise receipt, invoice, packing-slip, uncertain, sensitive, and forced-failure samples. Confirm all destinations are review-only and sensitive samples show no external provider call.
6. Re-run the controller and retry one eligible intake. Confirm destination counts do not increase.
7. Run the repository release-readiness, backup/restore, and rollback gates before requesting production approval.

Live staging deployment and acceptance require owner authorization and are not performed by this feature branch.

## Rollback

Application rollback is the preferred first action: restore the prior reviewed artifact while leaving the additive Backups tables intact. This preserves uploaded originals and intake evidence.

Only in a disposable or explicitly approved non-production environment, after exporting or confirming no Backups evidence must be retained, the schema migration can be reversed:

```bash
cd backend
alembic downgrade 20260802_0014
```

That downgrade drops the three Backups tables and their intake/audit/route data. It does not delete shared media originals or routed receipt/document records. Never run the downgrade against production without explicit owner approval and a verified backup.
