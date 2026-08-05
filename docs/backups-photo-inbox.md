# Backups photo inbox

Issue #154 adds a staging-first, single-photo document intake. Every authenticated account can submit one image. Submitters see only their own intake and original media; administrators and operations managers see the company queue. The existing media owner/management checks protect original-image reads.

The upload stores a controlled `backups` media asset whose first version and source document remain immutable. Repeating the same upload for the same account returns the existing intake using the SHA-256 identity rather than creating another intake.

## Daily controller

The unattended entry point is:

```bash
cd backend
python -m app.tools.backups_daily
```

A staging scheduler may invoke that command once daily. It reads pending rows only and does not use the ChatGPT application UI. Management can run the same controller from the Backups page or `POST /api/v1/backups/controller/daily` during staging acceptance.

The controller runs Tesseract locally first. Obvious banking, payroll, SIN, medical, and Luhn-valid full-card content is quarantined in Backups without an external request. Safe OCR text uses the configured OpenAI Responses API when `OPENAI_API_KEY` is present; otherwise conservative local rules are used.

Routing never approves, posts, pays, reconciles, accepts delivery, or selects a project:

- receipts create an existing receipt record in `needs_review`;
- supplier invoices create an unapproved `needs_review` document for the finance document queue;
- packing slips/delivery tickets create an unapproved `needs_review` document for the project/procurement queue;
- other, low-confidence, quarantined, and failed items stay in Backups management triage.

A project hint is retained as untrusted text metadata only. Failed, unrouted items can be reset to pending by management with a recorded reason. Unique media, uploader/hash, and destination constraints plus a single transaction for destination creation prevent retry duplication.

## Staging acceptance and rollback

Before acceptance, apply Alembic revision `20260805_0015`, upload a safe test image, run one controller pass, verify the audit history and review-only destination, and confirm the original is readable by its submitter/management but not another employee. Run a quarantined fixture and confirm no provider call.

Rollback is application-first: stop the staging scheduler, roll back the application release, and retain the two Backups tables for evidence. If an approved staging-only destructive schema rollback is required, create and verify a backup first, then downgrade one Alembic revision. Production deployment and production data changes remain outside this issue.
