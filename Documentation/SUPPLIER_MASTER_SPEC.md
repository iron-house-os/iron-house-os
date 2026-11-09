# Supplier Master Specification

This document defines the Iron House OS supplier master: the central database used for RFQs, price-list requests, supplier follow-up, bid coverage, quote tracking, bounced-email cleanup, and future supplier scoring.

## 1. Purpose

The supplier master should be the single source of truth for all suppliers and subcontractors used by Iron House.

It must support:

- Bid RFQ generation.
- Price-list request campaigns.
- Supplier category grouping.
- Preferred supplier routing.
- Bounced email tracking.
- Supplier reply monitoring.
- Quote history.
- Regional coverage.
- Future supplier scoring.

## 2. Workbook Structure

The first supplier master workbook should use these sheets:

```text
00_Master
01_Categories
02_Preferred_Suppliers
03_Price_Lists
04_RFQ_History
05_Bounced_Emails
06_New_Contacts
07_Do_Not_Use
08_Supplier_Scorecard
09_Notes
```

## 3. 00_Master Required Columns

| Column | Required | Notes |
| --- | --- | --- |
| Supplier ID | Yes | Unique ID for the supplier. |
| Company | Yes | Company name. |
| Category | Yes | Primary category. |
| Secondary Categories | No | Other scopes the supplier can price. |
| Contact Name | No | Estimator, sales rep, branch contact, or generic contact. |
| Email | Yes | Primary estimating or sales email. |
| Phone | No | Main or direct phone number. |
| Website | No | Source website. |
| Branch / Location | No | City or branch name. |
| Region | No | Lower Mainland, Fraser Valley, Interior, Island, etc. |
| Address | No | Physical branch address. |
| Status | Yes | Active, Preferred, Needs Verification, Bounced, Do Not Use, No Account, Archived. |
| Source | No | Web scrape, email reply, user supplied, quote, website, referral. |
| Source URL | No | Where the contact was found. |
| Last Contacted | No | Date of last RFQ or price-list request. |
| Last Response | No | Date of last supplier response. |
| Response Type | No | Quoted, declined, redirect, bounced, no account, price list, no reply. |
| Notes | No | Free-form notes. |

## 4. Category Standard

Use consistent categories so RFQs can be generated automatically.

Primary categories:

- Pipe / Utilities.
- Ductile Iron.
- Waterworks.
- Storm.
- Sanitary.
- Manholes / Catch Basins.
- Aggregates.
- Asphalt.
- Concrete Supply.
- Concrete Subcontractor.
- Sawcutting / Coring.
- Traffic Control.
- Pavement Markings.
- Electrical / Street Lighting.
- Testing / Inspection.
- Trucking.
- Disposal.
- Landscaping / Restoration.
- Geotextile / Geogrid.
- Rentals.
- Fuel / Consumables.
- General Civil Supplier.

Rules:

- Put suppliers with the same category together.
- Keep asphalt separate from general aggregate unless the company actively supplies both.
- Keep traffic-control suppliers grouped together.
- Keep pipe, waterworks, and utility suppliers grouped together.
- Keep testing firms separate from engineering consultants unless they provide field testing.

## 5. Preferred Supplier Defaults

Unless overridden by project-specific pricing, use these defaults:

| Scope | Preferred Supplier / Subcontractor |
| --- | --- |
| PVC pipe | EMCO |
| Ductile iron | EMCO |
| Catch basins | Amrize |
| Manholes | Amrize |
| Asphalt | Superior Paving |
| Testing | Advanced Testing |
| Concrete subcontracting | JWS |
| Coring | Performance Coring |

Preferred suppliers should be marked as `Preferred` in the Status field and also listed on `02_Preferred_Suppliers`.

## 6. Status Definitions

| Status | Meaning | RFQ Behaviour |
| --- | --- | --- |
| Active | Valid supplier contact. | Eligible for RFQs. |
| Preferred | Default supplier for one or more scopes. | Prioritized. |
| Needs Verification | Contact may be incomplete or unconfirmed. | Use only if coverage is weak. |
| Bounced | Email delivery failed. | Do not send until corrected. |
| Do Not Use | Supplier should not receive RFQs. | Excluded. |
| No Account | Supplier will not price without an account. | Excluded unless user approves. |
| Archived | Historic supplier no longer active. | Excluded. |

## 7. Source Tracking

Every scraped or manually added contact should record how it was found.

Source examples:

- User supplied.
- Company website.
- Google result.
- Supplier email reply.
- Delivery failure notice.
- Quote PDF.
- Price list.
- Referral from another supplier.
- BC construction directory.

When a source URL is available, record it.

## 8. Bounced Email Handling

When Gmail shows a delivery failure:

1. Record the email on `05_Bounced_Emails`.
2. Change supplier status to `Bounced`.
3. Add the bounce date.
4. Search for a replacement estimating email.
5. Add replacement contact to `06_New_Contacts` until verified.
6. Do not reuse the bounced email in RFQs.

Required bounced-email columns:

| Column | Notes |
| --- | --- |
| Company | Supplier company. |
| Bounced Email | Failed address. |
| Bounce Date | Date of delivery notice. |
| Project | Project associated with bounce. |
| Replacement Email | New candidate email, if found. |
| Status | Open, replaced, do not use, needs search. |
| Notes | Delivery notice details. |

## 9. Redirected Contact Handling

When a supplier reply provides a better estimating contact:

1. Add the new contact to `06_New_Contacts`.
2. Update `00_Master` if the new contact is clearly valid.
3. Keep the old email only if it remains useful.
4. Add note: `Redirected by [name/email] on [date]`.
5. Use the new contact for future RFQs.

## 10. Price List Handling

When a supplier provides a price list:

- Save the file in the supplier price-list folder.
- Record it on `03_Price_Lists`.
- Record effective date.
- Record expiry date, if any.
- Record category coverage.
- Record whether pricing includes delivery, taxes, fuel surcharge, minimums, and account requirements.

Required columns:

| Column | Notes |
| --- | --- |
| Company | Supplier. |
| Category | Material/service category. |
| Price List File | Path or link. |
| Effective Date | Start date. |
| Expiry Date | If provided. |
| Region | Pricing region. |
| Includes Delivery | Yes/no/unknown. |
| Includes Taxes | Yes/no/unknown. |
| Minimum Order | Notes. |
| Account Required | Yes/no/unknown. |
| Notes | Conditions, exclusions, surcharges. |

## 11. RFQ History

Every RFQ should create or update a record on `04_RFQ_History`.

Required columns:

| Column | Notes |
| --- | --- |
| Project | Project name/code. |
| Bid Close | Tender closing date. |
| Category | RFQ category. |
| Company | Supplier/subcontractor. |
| Email | Recipient. |
| Date Drafted | Draft creation date. |
| Date Sent | Sent date, if sent. |
| Quote Due | Requested quote deadline. |
| Reply Status | No reply, quoted, declined, redirected, bounced, question, no account. |
| Quote Amount | If applicable. |
| Quote File | Link/path. |
| Follow-Up Required | Yes/no. |
| Notes | Scope notes, exclusions, lead times. |

## 12. Supplier Scorecard

The long-term scorecard should track supplier reliability.

Suggested scoring factors:

- Response rate.
- Quote turnaround speed.
- Pricing competitiveness.
- Quote completeness.
- Scope accuracy.
- Delivery reliability.
- Relationship quality.
- Account requirements.
- Regional usefulness.
- Bid-day reliability.

Scorecard fields:

| Column | Notes |
| --- | --- |
| Company | Supplier. |
| Category | Scope category. |
| RFQs Sent | Count. |
| Quotes Received | Count. |
| Response Rate | Quotes/replies divided by RFQs sent. |
| Average Response Time | Days/hours. |
| Competitiveness | Low, medium, high, unknown. |
| Reliability Score | 1-5. |
| Preferred Status | Yes/no. |
| Notes | Qualitative notes. |

## 13. Duplicate Handling

Duplicate suppliers should be merged when:

- Company names are slightly different but clearly same branch.
- Same email appears under multiple rows.
- Same company has duplicate branch entries without distinct contacts.

Do not merge when:

- Different branches have different estimating contacts.
- Different divisions quote different categories.
- One contact is regional and one is branch-specific.

## 14. Data Quality Rules

The workbook should flag:

- Missing company name.
- Missing email.
- Invalid email format.
- Duplicate email.
- Duplicate company/category/branch combination.
- Status blank.
- Category blank.
- Bounced email still marked active.
- Do-not-use supplier included in RFQ.
- No-account supplier included without user approval.
- Price list past expiry.
- Preferred supplier missing from master.

## 15. Phase 1 Implementation

Phase 1 should support:

1. Clean master supplier sheet.
2. Standard category grouping.
3. Preferred supplier table.
4. Bounced email tracking.
5. New contact tracking.
6. RFQ history log.
7. Manual supplier scoring notes.
8. Manual updates from Gmail replies.

## 16. Future Automation

Later phases should support:

- Web-assisted supplier discovery.
- Email extraction from company pages.
- Gmail bounce detection.
- Gmail redirected-contact capture.
- Price-list attachment saving.
- Supplier quote extraction.
- Automatic category coverage warnings.
- Supplier scoring dashboard.
- Estimate workbook integration.
- RFQ draft generation from supplier master.
