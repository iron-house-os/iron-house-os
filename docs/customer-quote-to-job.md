# Customer Quote to Awarded Job

Issue: #249

Customer Quotes closes the gap between verbal customer information and the awarded-job controls already in IHOS.

## Workflow

1. Estimating or management records the customer, site, scope, pricing, assumptions, exclusions, validity, and notes.
2. IHOS creates a durable customer quote and links it to a new opportunity project, or to the selected project when supplied by the API.
3. Draft and sent quotes remain non-binding and have no job number.
4. A generated IHOS PDF can be opened for review or delivery through an approved company communication method. Marking a quote sent records status only; IHOS does not send it automatically.
5. Only an administrator or operations manager can use `Accept / award`. They must record the source of acceptance.
6. In one database transaction, IHOS records acceptance, awards the linked project, allocates the permanent no-hyphen `IHYYYYNNN` job number, and provisions the Project Workspace and job-start checklist.
7. Repeating the acceptance request returns the same job; it does not allocate another number.

## Controls

- Quote edits use an expected revision and reject stale overwrites.
- Accepted quotes are immutable.
- Declined or expired quotes require a new editable revision before they can re-enter the workflow.
- Customer Quotes is available to management and estimators, but acceptance is management-only.
- A draft, PDF, or sent status is not an award, contract acceptance, purchase order, or authorization to start work.
- This workflow does not send email, alter production, or perform external submissions.
- Preserved legacy IHOS job numbers and external source identifiers may retain their original punctuation; new IHOS job numbers do not.
