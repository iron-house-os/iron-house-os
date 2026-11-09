# Bennett staging original cost budget

## Objective

Complete issue #268 step 7 by carrying the immutable Bennett concrete estimate cost basis into awarded staging job `IH2026002` under the approved pilot cost codes.

## Financial boundary

Customer price and internal cost budget remain separate:

- accepted customer quote subtotal: `$36,266.67`;
- GST: `$1,813.33`;
- contract value: `$38,080.00`;
- original internal cost budget: `$26,660.93`.

The controlled allocation is recorded in `ops/staging-pilots/2026-08-28-bennett-cost-budget.json`. It produces five estimate-sourced budget entries across four job cost codes. It does not create commitments, actual costs, POs, invoices, accounting exports, or checklist completions.

## Application controls

- Management-only budget import accepts explicit source-to-job cost-code mappings.
- Existing manual budgets or another workspace budget block the import.
- Deterministic source keys make exact retries preserve budget-entry identity.
- Award metadata keeps customer pricing intact and stores detailed cost-budget lines separately.
- Approved project cost codes are available to daily timesheets.
- Launch readiness reports allocated budget status and zero uncoded cost-budget lines.

## Execution gate

The staging pilot runs only after a human merges the exact Build 229 pull request and that release deploys successfully to staging. It fails closed on release drift, record drift, source or amount drift, a conflicting budget, commitments or actuals, quote issuance, unsafe procurement state, or an unexpected job number.
