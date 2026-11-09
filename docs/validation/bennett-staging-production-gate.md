# Bennett staging field-production gate

## Purpose

Complete the safe pre-field portion of issue #268 step 10 for staging job `IH2026002`. Build 232 adds the controls needed to capture multiple field photos and multiple ticket images, then post an approved daily sheet atomically only after safety, portal, and mobilization controls are ready.

This staging gate does not create Day 1 or Day 2 records. Bennett remains blocked because project-specific safety evidence has not been verified, portal assignments have not been approved, and the awarded-job start checklist has not been completed.

## Controlled behavior

- A controlled post requires the exact awarded job, permanent job number, workspace, ready safety release and records, active project assignment, and complete start checklist.
- A blocked attempt creates no generated report, time entry, workspace folder, or posting manifest.
- A valid post creates the internal Field Production hierarchy, generated report reference, labour entries, and typed manifest in one transaction.
- A valid controlled retry returns the same record identities and does not duplicate entries.
- Field photos and ticket evidence are separate multiple-image collections linked to the selected project.
- Internal workspace paths do not create or claim external Google Drive folders.

## Shared-staging proof

After a human merges the exact Build 232 pull request and that exact main commit deploys successfully to staging, `Approved Bennett staging production gate`:

1. verifies the checkout, current `main`, approval marker, and live staging release are identical;
2. verifies the exact Bennett project, accepted draft-issue quote, estimate workspace, five-entry `$26,660.93` budget, four-item draft procurement plan, and blocked safety launch;
3. reads database counts before verification;
4. reads the live launch dashboard, awarded workspace, and daily-timesheet bootstrap without creating a business record;
5. verifies the exact safety, portal, mobilization, and production blockers, zero sheets/posts/reports/time entries/photos/tickets, and no Field Production folder; and
6. proves the protected counts are unchanged before uploading the report and release evidence for 90 days.

## Human gates that remain

The designated competent safety role must verify the project-specific safety requirements and evidence. Management must approve portal assignments and the responsible owners must complete the mobilization checklist. Only then may a field user enter actual Day 1 facts and evidence for management review and posting. Day 2 must be captured separately from its own actual field facts.

No production deployment, production record mutation, external issuance, vendor commitment, purchase order, actual cost, invoice, or accounting export is part of Build 232.
