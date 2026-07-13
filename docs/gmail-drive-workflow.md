# Gmail and Drive workflow design

Build 205 adds a connector-neutral workflow around the RFQ package builder. It prepares reusable package manifests, Gmail-ready draft plans, and supplier response references while keeping every Google-side action outside the application boundary.

## Safety boundary

- Preparing a workflow stores an IHOS manifest only. It does not create a Drive folder, upload a file, or create a Gmail draft.
- Draft plans are always returned as `preview_only` with `send_approved: false`.
- Sending supplier communication requires a separate, explicit approval and is not implemented by this build.
- Recording a response stores existing Gmail or Drive references. It does not read, move, copy, or modify those external items.

## Workflow

1. Add each supplier's estimating email to the supplier-specific scope.
2. Complete RFQ readiness and attach Drive or storage references.
3. Save a reusable draft workflow with a Drive folder reference and optional manifest reference.
4. Review the generated Gmail draft plan, blockers, recipients, and attachments.
5. After a response arrives outside IHOS, register its Gmail thread or Drive file reference. IHOS marks that supplier as replied.

The saved plan includes a fingerprint of the package recipients, scopes, dates, and attachment references. IHOS reports the workflow as stale whenever those inputs change.

## API

- `GET /api/v1/rfqs/{id}/communication-workflow` returns the persisted preview and supplier response index.
- `POST /api/v1/rfqs/{id}/communication-workflow/prepare` stores a reusable Drive manifest record and Gmail-ready draft plans.
- `POST /api/v1/rfqs/{id}/supplier-responses` stores an existing Gmail thread or Drive file reference and marks the supplier replied.

## Persistence

The workflow manifest, supplier contact emails, and response index are stored in `RFQPackage.metadata_json`. This keeps Build 205 migration-free and preserves package portability. A future connector implementation can move these records into dedicated tables without changing the public API.

## Known limitations

- Gmail and Drive APIs are not called; OAuth and provider adapters remain future work.
- Attachment and response references must be entered or selected by the user.
- Supplier responses are indexed but their files and message bodies are not ingested.
- Concurrent edits use the RFQ package's normal last-write behavior; provider-side version reconciliation is not implemented.
