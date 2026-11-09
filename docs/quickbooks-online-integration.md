# QuickBooks Online integration

Issue: #389. This document describes the first, read-only IHOS slice and the gates for a later sandbox connection. The ChatGPT QuickBooks plugin does not connect IHOS to QuickBooks.

## Current behaviour

Financial Control has a **QuickBooks preview** action on each customer invoice. It reads the IHOS record, checks the source arithmetic and status, and returns a list of blockers. It never calls Intuit, stores credentials, creates an accounting record, or marks an invoice exported. The API is management-only:

`GET /api/v1/finance/customer-invoices/{invoice_id}/quickbooks-preview`

An invoice passes IHOS source checks only when it has recorded issuance, a non-trash awarded/construction/completed project, no development seed marker, a unique invoice number, and line/subtotal/GST/total values that reconcile to the cent. Source checks do **not** grant accounting export. `export_enabled` is always false until a separately reviewed implementation supplies customer, tax, item, source PDF and duplicate mappings.

## Intended ownership

| Record | Owner | Direction |
| --- | --- | --- |
| Job, completed work, quote and invoice approval evidence | IHOS | Retain source IDs and final file references. |
| Posted invoice, tax treatment, accounts receivable and payments | QuickBooks Online | Read back the QuickBooks ID and balance only after a verified sandbox transfer. |
| Customer, product/service, GST/PST and chart-of-accounts mapping | Accounting review | Match exact existing QuickBooks IDs; never guess from name alone. |

## Next build gates

1. Register an Intuit developer app and connect a **sandbox** company with server-side OAuth 2.0. Validate state and redirect, encrypt refresh tokens, bind the exact company realm, and support disconnect. Keep credentials out of code and client storage.
2. Add a transfer journal keyed by `(realm_id, ihos_invoice_id)`, with the QuickBooks invoice ID, source version, request fingerprint and result. Before any create, search QuickBooks for the exact document number and customer. If a request times out, reconcile remotely before retrying.
3. Have the company's bookkeeper approve the Canadian tax code, product/service item, income account and rounding behaviour using representative invoices. Reject mismatches. Do not automatically email invoices, record payments, export payroll, or post receipts.
4. Exercise duplicate, timeout, revocation and tax-conflict cases in the sandbox. Run CI and staging. Production connection and accounting writes require separate owner approval through normal IHOS release controls.

Intuit references: [OAuth 2.0](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0), [sandbox](https://developer.intuit.com/app/developer/qbo/docs/develop/sandboxes), [invoice API](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/invoice).
