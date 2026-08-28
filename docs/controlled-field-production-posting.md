# Controlled field-production posting

## Purpose

Approved daily timesheets are the source record for crew labour, equipment use, material and production quantities, field narrative, field photos, and delivery or disposal tickets. Controlled posting converts one approved sheet into project-bound operational records without silently releasing an unready job or creating external folders.

## Evidence types

Daily sheets keep field photos and ticket evidence as separate, multi-file lists. Every attachment must be an active document on the selected project. One document cannot be classified as both a field photo and ticket evidence on the same sheet.

The sheet continues to support multiple labour cost-code splits, owned and rental equipment, materials, receipts, measured production quantities, weather and site conditions, potential-change flags, and safety/quality notes. These are field-entered facts; IHOS does not infer them.

## Controlled posting gate

For a project with the controlled safety-launch record, management can post an approved or exported daily sheet only when all of these conditions are true:

- the project is awarded or in construction;
- a permanent job number and awarded workspace exist;
- the safety release is `ready`, with every applicable requirement linked to a ready record;
- project portal access is active with at least one active assignment; and
- every awarded-job start checklist item is complete.

Any unresolved condition returns `409` and creates no time entries, generated report, folder entry, or posting manifest.

Legacy projects without a controlled safety launch retain their existing posting behavior until deliberately migrated. This preserves existing records while the controlled gate is introduced job by job.

## Atomic post and retry

A successful controlled post performs one database transaction:

1. prepares the internal `13_Award_Handoff/Field_Production` hierarchy once;
2. creates one project-linked generated daily-report document reference;
3. creates approved labour time entries for the sheet's cost-code splits; and
4. saves a typed `production_post` manifest on the daily sheet.

The manifest records the permanent job number, exact sheet/version posting key, report and folder paths, separate photo and ticket document IDs, cost-code quantity summary, time-entry IDs, actor, and time. A valid retry returns the same post. It does not duplicate records. A mismatched or incomplete existing manifest fails closed for management review.

The workspace paths are internal IHOS manifest entries only. No Google Drive folder or external file is created or claimed.

## Day 1 and Day 2 operating sequence

After the responsible safety and operations roles release the project and assign portal access, the designated field user records the actual Day 1 sheet and attaches the actual evidence. Management reviews and approves it, then posts it. Day 2 follows as a separate dated sheet. Actual dates, people, hours, quantities, conditions, notes, photos, and tickets must come from the work; they must never be prefilled as staging proof.

The launch dashboard shows whether controlled posting is blocked or ready, the current blocker codes, daily-sheet and production-post counts, the latest sheet status, and whether the internal field-production folder hierarchy has been prepared.
