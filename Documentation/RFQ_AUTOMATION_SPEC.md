# RFQ Automation Specification

This document defines how Iron House OS should generate, track, and manage supplier and subcontractor RFQs for civil construction bids.

## 1. Purpose

The RFQ automation system turns a bid package into organized supplier requests. It should reduce manual drafting, keep supplier communication consistent, attach the correct files, and track quote status until bid close.

## 2. Inputs

The RFQ builder uses the following inputs:

- Project name.
- Tender number.
- Owner / municipality.
- Bid closing date and time.
- Quote return deadline.
- Project location.
- Scope summary.
- Drawing package.
- Specifications.
- Addenda.
- Municipal standards checklist output.
- Bid intake and drawing review checklist output.
- Quantity takeoff workbook.
- Supplier master workbook.
- Default supplier preferences.
- Trade/category package requirements.

## 3. Required Project Folder Inputs

Each project should have these folders before RFQs are generated:

```text
01_Tender_Documents/
02_Drawings/
03_Addenda/
04_Takeoff/
05_Estimate/
06_RFQs/
07_Supplier_Quotes/
08_Submission/
09_Post_Bid/
```

The RFQ builder should pull attachments from:

- `02_Drawings/`
- `03_Addenda/`
- `04_Takeoff/`
- Relevant extracted specification pages, if available.

## 4. Supplier Master Requirements

The supplier master must include, at minimum:

| Field | Required | Notes |
| --- | --- | --- |
| Company | Yes | Supplier or subcontractor name. |
| Category | Yes | Pipe, aggregate, asphalt, concrete, traffic, testing, etc. |
| Contact Name | No | Use when known. |
| Email | Yes | RFQ cannot send without this. |
| Phone | No | Useful for follow-up. |
| Region | No | Helps match local suppliers. |
| Notes | No | Account status, quote preferences, bounced emails, special instructions. |
| Status | Yes | Active, do not use, needs verification, bounced, preferred. |
| Last Contacted | No | Updated when RFQ draft is created or sent. |
| Last Response | No | Updated from Gmail monitoring. |

## 5. RFQ Package Categories

The system should generate packages for these categories when the scope requires them:

- Pipe and utility materials.
- Manholes and catch basins.
- Aggregates and granular materials.
- Asphalt paving.
- Concrete subcontracting.
- Concrete supply, if separate.
- Sawcutting and coring.
- Traffic control.
- Pavement markings.
- Street lighting and electrical.
- Testing and inspection.
- Trucking and disposal.
- Landscaping and restoration.
- Specialty items identified in the drawings.

## 6. Default Supplier Routing

Unless a project-specific supplier is selected, use Iron House defaults where available:

| Scope | Default Supplier / Subcontractor |
| --- | --- |
| PVC pipe | EMCO |
| Ductile iron | EMCO |
| Catch basins | Amrize |
| Manholes | Amrize |
| Asphalt | Superior Paving |
| Testing | Advanced Testing |
| Concrete subcontracting | JWS |
| Coring | Performance Coring |

The system should still generate backup RFQs to comparable suppliers when quote coverage is weak or pricing risk is high.

## 7. Attachment Rules

Each RFQ must include enough information for the supplier to price without asking for basic project documents.

### Pipe / Utility RFQ Attachments

- Overall civil drawings.
- Utility plan and profile sheets.
- Pipe schedules.
- Details for trenching, bedding, tie-ins, services, and structures.
- Relevant municipal standards.
- Addenda affecting utilities.

### Aggregate RFQ Attachments

- Site plan.
- Roadworks sections.
- Granular material specifications.
- Quantity summary.
- Delivery location and access notes.

### Asphalt RFQ Attachments

- Paving plan.
- Road sections.
- Asphalt mix and thickness requirements.
- Tie-in, milling, sawcut, and restoration details.
- Traffic staging notes.

### Concrete RFQ Attachments

- Concrete plan and details.
- Curb, sidewalk, letdown, driveway, pad, and bollard sleeve details.
- Concrete specifications.
- Reinforcement details.
- Finish requirements.

### Traffic Control RFQ Attachments

- Location plan.
- Work limits.
- Construction staging notes.
- Lane closure requirements.
- Pedestrian and cyclist routing requirements.
- Work-hour restrictions.

### Testing RFQ Attachments

- Specifications.
- Municipal testing requirements.
- Scope breakdown.
- Estimated quantities.
- Schedule assumptions.

## 8. Email Draft Standard

Each RFQ email should include:

- Professional Iron House greeting.
- Project name.
- Project location.
- Bid closing date.
- Quote return deadline.
- Requested scope.
- Attachment reference.
- Request to include exclusions, lead times, delivery, taxes, and validity.
- Redirect sentence if the RFQ reached the wrong inbox.
- Iron House signature.

## 9. Standard RFQ Email Body

```text
Hello,

Iron House is pricing the following project and would appreciate your quotation for the applicable scope.

Project: [PROJECT NAME]
Location: [PROJECT LOCATION]
Owner / Municipality: [OWNER]
Tender Close: [BID CLOSING DATE AND TIME]
Requested Quote Return: [QUOTE RETURN DEADLINE]

Requested scope:
[SCOPE BULLETS]

Please include applicable supply, delivery, taxes, lead times, exclusions, quote validity, and any assumptions required for your pricing. Relevant drawings/specifications are attached for reference.

If this RFQ has reached the wrong inbox, please forward it to the correct estimator or provide the best estimating contact for future requests.

Thank you,

Iron House
[NAME]
[PHONE]
[EMAIL]
```

## 10. RFQ File Naming

RFQ outputs should use consistent naming:

```text
RFQ_[ProjectCode]_[Category]_[Company]_[YYYY-MM-DD].eml
RFQ_[ProjectCode]_[Category]_[Company]_[YYYY-MM-DD].pdf
RFQ_Log_[ProjectCode].xlsx
```

Examples:

```text
RFQ_WR26-012_Asphalt_SuperiorPaving_2026-07-04.eml
RFQ_WR26-012_Pipe_EMCO_2026-07-04.eml
RFQ_Log_WR26-012.xlsx
```

## 11. RFQ Log Fields

The RFQ log should include:

| Field | Notes |
| --- | --- |
| Project | Project name or code. |
| Category | Scope category. |
| Company | Supplier or subcontractor. |
| Contact | Person, if known. |
| Email | RFQ recipient. |
| Attachments | Drawing/spec files included. |
| Sent/Drafted Date | Date created or sent. |
| Quote Due | Supplier quote deadline. |
| Status | Drafted, sent, replied, quoted, declined, bounced, follow-up required. |
| Quote Amount | Total quoted value, if applicable. |
| Quote File | Link/path to saved quote. |
| Notes | Exclusions, lead times, alternate pricing, account issue, etc. |

## 12. Gmail Integration Requirements

When Gmail is connected, the RFQ system should:

- Create reviewable drafts unless the user explicitly asks to send.
- Attach the appropriate files when supported.
- Keep the subject line consistent.
- Avoid sending to bounced or do-not-use contacts.
- Save one draft per supplier or subcontractor.
- Track created drafts in the RFQ log.
- Monitor replies for quotes, bounce notices, redirected contacts, and new estimating emails.

## 13. Reply Monitoring Rules

When supplier replies are reviewed, the system should capture:

- Quote received.
- Decline to quote.
- No account / cannot quote.
- Wrong contact / redirected estimator.
- Bounce or delivery failure.
- Price list attached.
- New supplier contact.
- Clarification question.
- Scope exclusion.
- Lead-time risk.

Updates should be written back to the supplier master and project RFQ log.

## 14. Error Handling

The system should flag:

- Missing supplier email.
- Bounced email.
- Duplicate supplier.
- Missing attachments.
- No drawing package.
- No quote return deadline.
- Supplier marked do-not-use.
- Category with no supplier coverage.
- Scope item without an RFQ package.

## 15. Minimum Viable Workflow

Phase 1 implementation should support:

1. Read supplier master workbook.
2. Select active suppliers by category.
3. Build RFQ scope bullets from project scope.
4. Generate standard email body.
5. Create Gmail drafts for review.
6. Record drafts in RFQ log.
7. Monitor replies manually or through Gmail search.
8. Update supplier master with bounced emails, redirects, and quote status.

## 16. Future Automation

Later phases should add:

- Attachment selection by drawing sheet tag.
- Automatic quote extraction from email attachments.
- Supplier scoring by response rate and competitiveness.
- Category coverage warnings.
- Follow-up reminders before quote deadline.
- Automatic bid-day quote comparison.
- Integration with estimate workbook.
- Integration with tender discovery pipeline.
