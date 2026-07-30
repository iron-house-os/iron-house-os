# Sprint 2C — Durable Quote-to-Estimate Handoff

## Objective

Move approved project supplier pricing into the project estimate without browser-only state, manual re-entry, destructive updates, or duplicate cost allowances.

## Build register

- Trigger: an estimator selects **Use selected quotes in estimate** after saving and comparing project quotes.
- Inputs: project ID, persisted project quotes, current quote revisions and selections, and the latest parseable draft estimate workspace.
- Steps: reload saved project quotes; revalidate eligibility and selection; load the latest draft estimate; merge pricing by normalized line code; recalculate the estimate; save an immutable draft snapshot; open Estimating from the database.
- Decision points: quote completeness, multiple selections, non-low selection reason, quote eligibility, line-code ambiguity, and whether an identical handoff already exists.
- Owner: Iron House estimator.
- Approval gate: human review before issuing any final estimate or bid.
- Output: auditable draft estimate snapshot with source quote IDs and source workspace ID.
- System of record: Iron House OS `quotes` and `bids` tables.
- Review frequency: each accepted supplier quote revision or estimate-scope update.
- Failure modes: missing project, incomplete selection, unqualified or zero quote, ambiguous estimate code, invalid draft estimate, or duplicate handoff.

## Controls

- The handoff API accepts only a project ID; it reloads quotes from the database.
- Quotes from another project cannot enter the handoff.
- The source estimate and quote records are never modified.
- Quantity, unit, production, labour, equipment, disposal, indirects, risks, markups, assumptions, and exclusions are preserved.
- Conflicting direct, material, or subcontract allowances are cleared for the supplier-priced cost class.
- A fresh estimate summary is stored with every new snapshot.
- Repeating an unchanged handoff returns the existing snapshot.
- Duplicate normalized estimate line codes fail closed.
- Production remains unchanged until the staged PR chain is reviewed and approved.
