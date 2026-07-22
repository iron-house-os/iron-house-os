# Build 228 — Startup Costs & Owner Loan Ledger

## Purpose
Track legitimate Iron House startup purchases paid personally by an owner/shareholder until the company reimburses them.

## Financial Control
- Adds a management-only **Startup costs / owner loan** ledger separate from job-cost project ledgers.
- Default funding source is **Owner/Shareholder Loan Payable**.
- Receipt lifecycle: `review` → `approved` → `reimbursed`, with `void` for rejected/non-business items.
- Reimbursement changes the loan balance but does not create a second expense.
- Tracks current-expense / capital-asset / needs-review tax treatment for accountant review.
- Provides a QuickBooks-friendly startup ledger CSV.

## Receipt intake
The ledger stores vendor, date, description, amount, category, order/invoice reference, source email, owner, and receipt metadata. Email-sourced receipts can be staged in `review` until the owner confirms business purpose.

## Accounting guardrail
The OS records the bookkeeping intent and preserves receipt evidence. Final deductibility, GST/HST input-tax-credit eligibility, current-vs-capital treatment, and shareholder-loan presentation remain subject to accountant review.
