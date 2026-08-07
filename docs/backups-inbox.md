# Backups photo inbox

Issue: #154. Backups is a single-photo, review-only document intake path. It reuses the private media store and does not approve, post, pay, reconcile, or accept any routed record.

## Data flow

1. An authenticated user uploads exactly one image to the existing media API with category `backup`.
2. `POST /api/v1/backups` binds that immutable original media ID and SHA-256 hash to one intake and records the uploader's identity and portal role.
3. The daily controller atomically claims each pending intake once and reads the original media version.
4. Local OCR runs before classification. Banking, payroll, SIN, medical, or valid full-card content is quarantined without an external request.
5. When configured and permitted, the OpenAI Responses API receives only screened OCR text, uses a strict four-label schema, and has `store` disabled. Local heuristics are the offline/failure fallback.
6. Every analyzed item enters `finance_intake`, including unknown, low-confidence, and quarantined items. Analysis does not create, approve, post, export, reconcile, pay, or accept a financial or delivery record.
7. Management can change the single review destination to Finance Receipts, Finance Invoices, Finance Packing Slips, or Backups Needs Review. A compare-and-set update prevents competing reviewers from overwriting each other, and selecting the current destination is idempotent.

The intake status is one of `pending`, `processing`, `routed`, `needs_review`, or `failed`. Audit events record submission, claim, analysis/triage/failure, retry, and every destination change with its actor, timestamp, previous destination, and new destination. The unique intake media ID and single destination column prevent duplicate destination records.

## Authorization

- Every authenticated administrator, management user, estimator, employee, foreman, and operator can submit.
- Non-management users can list/read only their own intake records and original images.
- Management and administrators can view the company queue and Finance review queues, change destinations, run the controller, and retry failed or triage records.
- Routing changes queue placement only. Receipt approval/export/reconciliation and payment controls remain management-only; packing slips never confirm delivery, quantity, quality, acceptance, or project cost.
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

Only in a disposable or explicitly approved non-production environment, the management-routing schema can be reversed without dropping the original Backups tables:

```bash
cd backend
alembic downgrade 20260805_0015
```

That downgrade removes only the review-destination column and index. It preserves uploaded originals, uploader identity, intake records, legacy route records, and audit events. Never run the downgrade against production without explicit owner approval and a verified backup.
