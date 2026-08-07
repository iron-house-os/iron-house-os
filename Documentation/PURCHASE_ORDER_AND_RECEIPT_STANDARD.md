# Iron House Purchase Order and Receipt Standard

## Rule

For company purchases, the normal field workflow is:

**Request PO in IHOS -> make the purchase -> put the IHOS PO number on the receipt/invoice -> submit the receipt to Dext -> done.**

The employee, operator, foreman, cardholder, or other purchaser is responsible for obtaining and using the correct IHOS PO number where practical. IHOS and the Dext integration are responsible for the downstream receipt matching and coding workflow.

## Required field action

1. Before a planned purchase, open **Request PO** in IHOS and select the correct job.
2. Use the automatically generated IHOS PO number for the purchase.
3. Give the PO number to the supplier and have it printed or written on the receipt or invoice whenever possible.
4. Submit a clear image or electronic copy of the receipt to Dext promptly after the purchase.
5. Do not manually guess accounting categories, equipment, vehicle, business purpose, or cardholder coding unless IHOS asks for clarification.

## PO format

IHOS PO numbers contain the job number so accounting and receipt processing can identify the project automatically. Example:

`PO-000127-26-014`

## Exceptions

- Emergency or unplanned purchases may be made without a pre-issued PO when delaying the purchase would materially affect safety, site operations, equipment protection, or production. The purchaser must still submit the receipt to Dext and provide the correct job information as soon as practical.
- If a supplier cannot place the PO on the receipt, enter the IHOS PO in the available Dext PO/reference field when possible.
- If neither a valid PO nor a verified job number is available, IHOS must route the receipt to **Needs review** rather than guessing the job.
- A receipt submitted to Dext is evidence of the purchase; submission does not by itself constitute management approval of the expenditure.

## System responsibilities

The Dext -> Zapier -> IHOS integration should, when data is available:

- match the receipt to the IHOS PO;
- resolve the job number from the PO;
- retain the original Dext receipt data and image reference;
- prevent duplicate receipt records;
- classify expense category, business purpose, equipment/vehicle, and employee/cardholder where confidence is sufficient;
- route uncertain or conflicting records to review instead of silently posting them.

## Management control

Management may define purchases, dollar thresholds, vendors, or categories that require approval before a PO is issued. Rework and other designated exception categories remain subject to management review regardless of automated receipt classification.
