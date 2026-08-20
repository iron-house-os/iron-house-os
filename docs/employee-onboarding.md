# Employee onboarding

IHOS employee onboarding is available to administrators under the employee onboarding module and to invited employees through a secure token link.

## Controlled positions

Field staff: Green Labourer, Labourer, Skilled Labourer, Junior Pipelayer, Senior Pipelayer, Grademan / Top Man, Equipment Operator, Foreman, Superintendent.

Office staff: Admin, Controller, Project Manager, CFO, COO, CEO, President.

## Workflow

1. An administrator creates a draft onboarding record.
2. IHOS issues a hashed, expiring invitation token.
3. The invitation can be delivered as a direct link or a locally generated QR code. A resend invalidates the previous link and QR.
4. The employee opens one IHOS portal and completes the assigned personal information, address, emergency contact, payroll, 2026 TD1/TD1BC, agreements, certification, and PPE forms.
5. Each form is validated by IHOS, encrypted before storage, and can be saved and resumed while the invitation is valid.
6. The employee reviews the completed packet, certifies it with a typed electronic signature, and submits it.
7. An administrator can open the restricted packet through an audited management-only action, request corrections, or approve the submission.
8. Supervisor-led safety orientation, qualification verification, competency assessment, and deployment readiness remain separate IHOS controls. Only an approved and deployment-ready onboarding can be activated into an employee record.
9. Activated employees enter through Employee Portal unless they hold the separate Foreman Portal role. Equipment Operator remains a workforce classification; it does not create a standalone portal or grant equipment-operation authority.

## Restricted data controls

- Banking, SIN, date-of-birth, emergency-contact, and tax values are encrypted at rest using an IHOS-specific key derived from the protected application secret.
- `SECRET_KEY` is therefore also the current restricted-packet decryption root. Rotating or replacing it without first decrypting and re-encrypting every stored packet will make those packets unreadable. Treat any rotation as a controlled data migration with backup and disposable-staging recovery evidence before production approval.
- Restricted values are excluded from invitation emails and QR codes, onboarding list responses, logs, and audit metadata.
- Management access to the decrypted packet is administrator-only and creates an audit event.
- Invitation links and QR codes are bearer credentials. They expire, must not be forwarded, and are invalidated when a new invitation is issued.

## 2026 TD1 sources

The in-portal tax fields follow the current Canada Revenue Agency forms for pay received in 2026:

- Federal TD1: https://www.canada.ca/en/revenue-agency/services/forms-publications/td1-personal-tax-credits-returns/td1-forms-pay-received-on-january-1-later/td1.html
- British Columbia TD1BC: https://www.canada.ca/en/revenue-agency/services/forms-publications/td1-personal-tax-credits-returns/td1-forms-pay-received-on-january-1-later/td1bc.html

The employee is responsible for the amounts entered. IHOS does not calculate eligibility or provide tax advice.

For a non-resident, IHOS requires the federal TD1 90%-of-world-income answer. A "No" answer forces all federal claim lines to zero, matching the 2026 TD1 direction.

## Open controlled-document item

The repository does not yet contain an approved employment agreement set or complete employee handbook for assignment in this portal. The current agreements section is an employee acknowledgement and includes the approved purchase/receipt rule; it must not be treated as evidence that an unavailable agreement or handbook was assigned or viewed. Controlled-document assignment, version display, opening evidence, and acknowledgement history remain open until management supplies approved source documents.

## Purchasing and receipt rule

All employees, operators, foremen, cardholders, and other purchasers must follow the Iron House purchase and receipt workflow for company purchases:

**Request PO in IHOS -> make the purchase -> put the IHOS PO number on the receipt/invoice -> submit the receipt to Dext -> done.**

Employees are responsible for selecting the correct job when requesting the PO, using the generated PO with the supplier where practical, and submitting a clear receipt to Dext. Employees should not guess accounting categories, equipment/vehicle coding, business purpose, or cardholder coding unless IHOS requests clarification.

Emergency or unplanned purchases may proceed without a pre-issued PO when delaying the purchase would materially affect safety, site operations, equipment protection, or production. The receipt must still be submitted promptly and the correct job information supplied as soon as practical.

The complete rule is maintained in `Documentation/PURCHASE_ORDER_AND_RECEIPT_STANDARD.md`.

Production email delivery and activation remain subject to management approval and environment configuration.
