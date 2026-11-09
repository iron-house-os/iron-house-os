# Bennett staging procurement plan

## Objective

Complete issue #268 step 8 by turning the awarded Bennett concrete estimate and allocated original budget into four traceable procurement planning requirements for job `IH2026002`.

## Planning boundary

The plan records one material-planning item, two rental-planning items and one trucking-planning item. Every requirement carries its immutable estimate source, budget source key, job number, approved cost code, scope basis and source estimate-line cost. That cost is labelled as provenance, not authorized procurement spend.

The ready-mix order quantity remains `needs_confirmation`. The estimate's 108.60 m² scope quantity is not silently converted into a purchase quantity. The `$4,750.00` subgrade/buried-deficiency allowance remains only in the original cost budget.

## Application controls

- Management-only estimate-budget import accepts explicit procurement planning requirements.
- Server-side matching derives job number, cost code and budget provenance from the selected estimate and allocated budget.
- Deterministic requirement keys make exact retries stable.
- A progressed plan, vendor choice, quote reference, required date, approval, PO or commitment blocks regeneration.
- Plan status remains draft and automatic commitments remain disabled.
- No PO request, booking, actual cost, invoice, checklist completion or external issuance is created.

## Execution gate

The staging pilot runs only after a human merges the exact Build 230 pull request and that release deploys successfully to staging. It fails closed on release drift, record drift, source or amount drift, an unsafe procurement baseline, a changed original budget, an inferred ready-mix order quantity, or any prohibited downstream record.
