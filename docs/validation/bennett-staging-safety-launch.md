# Bennett staging safety launch

## Purpose

Complete the bounded initialization portion of issue #268 step 9 for awarded staging job `IH2026002` without creating safety evidence, assigning portal access, or authorizing mobilization.

Build 231 prepares one internal `13_Award_Handoff/Safety` path, a six-requirement safety launch shell, and an empty project portal assignment control. Every requirement starts `not_started` with applicability `unconfirmed`; the overall safety release remains `blocked`.

## Controlled behaviour

- Initialization requires an awarded project with a permanent job number and existing workspace.
- Retry returns the same initialized shell and does not duplicate the internal folder entry.
- The internal folder entry is an IHOS manifest path only. It does not create or claim a Google Drive folder.
- No `FieldRecord` safety evidence is created.
- Portal access starts `not_started`, with zero assignments and automatic provisioning disabled.
- Viewer/field accounts cannot see or post directly to an initialized controlled job unless a later explicit active project assignment exists.
- Legacy projects without this control retain their current portal behaviour until deliberately migrated.
- Mobilization readiness remains derived only from the ten-item project-start checklist; Build 231 completes none of those items.

## Shared-staging proof

After a human merges the exact Build 231 pull request and the exact main commit deploys successfully to staging, `Approved Bennett staging safety launch`:

1. verifies the checkout, current `main`, approval marker, and live staging release are identical;
2. verifies the exact Bennett project, accepted draft-issue quote, concrete estimate workspace, five-entry `$26,660.93` cost budget, and four-item draft procurement plan;
3. reads database counts for user accounts, employees, onboarding rows, project safety records, and completed start controls;
4. initializes and retries the safety launch through the authenticated live HTTPS staging API;
5. verifies the exact blocked shell, single internal Safety path, empty portal assignment control, zero safety evidence, and unchanged protected counts; and
6. uploads the report, release readiness payload, and run metadata as 90-day evidence.

## Human gates that remain

The designated competent safety role must verify project-specific conditions, requirements, hazards, controls, emergency response, first aid, qualifications, and evidence. Management must explicitly assign each portal recipient. The responsible field person must verify conditions at the work location. Those actions, any mobilization release, and all production changes are outside this workflow.
