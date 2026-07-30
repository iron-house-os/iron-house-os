# Sprint 2B — Project Quote Register

## Objective

Preserve supplier quote pricing, qualification, and selection decisions inside the correct project instead of treating Quote Comparison as a temporary calculator.

## Build register

- Trigger: an estimator opens Quote Comparison from Project Workspace.
- Inputs: project context, supplier, optional RFQ/RFQ-package and supplier links, quote reference and revision, estimate line, scope, status, amount, qualifications, exclusions, and selection reason.
- Steps: load project quotes; create or update records; validate linked records against the same project; compare current revisions; preserve selection reasons; hand selected pricing to Estimating.
- Decision points: quote eligibility; latest revision; lowest qualified quote; documented reason for a non-low selection.
- Owner: Iron House estimator.
- Approval gate: human review before using selected quote pricing in a final estimate or bid.
- Output: project-scoped supplier quote records and an estimate handoff.
- System of record: Iron House OS `quotes` table.
- Review frequency: each supplier response or quote revision.
- Failure modes: missing project, cross-project RFQ link, missing supplier record, incomplete quote, multiple selections, or undocumented non-low selection.

## Controls

- Every saved quote has a required `project_id`.
- RFQ and RFQ-package links are rejected when they belong to another project.
- Saved quotes cannot be removed from Quote Comparison; mark obsolete pricing rejected and enter revised pricing as a newer revision.
- Comparison continues to block incomplete, unqualified, bounced, declined, rejected, or undocumented non-low selections.
- Production remains unchanged until the dependent staging PR chain is reviewed and approved.

## Known limitations

- Quote documents and email responses are not parsed into line items automatically.
- The first release records quote data manually and does not expose destructive deletion.
- Project-level estimate persistence remains separate from the Quote Comparison handoff.
