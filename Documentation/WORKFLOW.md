# Iron House OS Workflow

This document defines the end-to-end Iron House OS workflow from tender discovery to post-bid review and awarded-project handoff.

## 1. Workflow Purpose

Iron House OS is designed to turn civil construction opportunities into organized bid packages with consistent review, estimating, supplier RFQs, submission controls, and post-bid learning.

The workflow should make every bid repeatable:

```text
Find opportunity → Screen → Create project folder → Review documents → Check standards → Take off quantities → Send RFQs → Build estimate → Review risk → Submit bid → Track results → Improve system
```

## 2. Workflow Stages

| Stage | Name | Output |
| --- | --- | --- |
| 1 | Tender Discovery | Candidate opportunity list. |
| 2 | Go / No-Go Screen | Bid/no-bid decision. |
| 3 | Project Setup | Standard project folder and index. |
| 4 | Document Intake | Tender docs, drawings, addenda, standards saved. |
| 5 | Drawing Review | Scope, risks, missing info, RFIs. |
| 6 | Municipal Standards Review | Cost and compliance impacts. |
| 7 | Quantity Takeoff | Measured quantities and scope breakdown. |
| 8 | RFQ Packaging | Supplier and subcontractor requests. |
| 9 | Estimate Build | Direct costs, indirects, risk, markup, final price. |
| 10 | Bid Review | Submission-ready package. |
| 11 | Submission | Final bid submitted and confirmation saved. |
| 12 | Post-Bid Review | Bid results, quote comparison, lessons learned. |
| 13 | Award Handoff | Construction startup package if awarded. |

## 3. Stage 1: Tender Discovery

Goal: find civil construction opportunities that fit Iron House.

Sources may include:

- BC Bid.
- CivicInfo BC.
- Municipal procurement pages.
- Regional district procurement pages.
- School district procurement pages.
- Port, utility, and public agency opportunities.
- Consultant-issued invitations.
- Direct owner requests.

Discovery output:

- Opportunity name.
- Owner.
- Location.
- Closing date.
- Mandatory meeting status.
- Estimated scope.
- Document link.
- Initial fit rating.

## 4. Stage 2: Go / No-Go Screen

Use `BID_INTAKE_AND_DRAWING_REVIEW_CHECKLIST.md`.

Screen for:

- Location.
- Size.
- Scope fit.
- Bonding requirements.
- Schedule.
- Working capital exposure.
- Specialty subcontractor risk.
- Traffic-control risk.
- Environmental risk.
- Mandatory experience requirements.
- Submission complexity.

Output:

```text
GO, NO-GO, or WATCH
```

If the project is a no-go, save the reason in the tender tracker.

## 5. Stage 3: Project Setup

Use `PROJECT_FOLDER_STANDARD.md`.

Create:

```text
[YYYY-MM-DD_CloseDate]_[Owner]_[ProjectCode]_[ShortProjectName]/
```

Create the standard folder tree and `PROJECT_INDEX.md`.

Project index must include:

- Project name.
- Tender number.
- Owner.
- Consultant.
- Closing date.
- Bid status.
- Estimator.
- Key files.
- Key risks.
- Open RFIs.
- Bid qualifications.

## 6. Stage 4: Document Intake

Save all tender documents into the correct folders:

- Tender documents into `01_Tender_Documents`.
- Drawings into `02_Drawings/Current`.
- Addenda into `03_Addenda`.
- Municipal standards into `04_Standards_and_Specs`.
- Correspondence into `10_Correspondence`.

Document intake checks:

- Confirm drawing issue date.
- Confirm addenda count.
- Confirm tender form and schedule are present.
- Confirm specifications are present.
- Confirm submission instructions are clear.
- Confirm mandatory meeting or site visit requirements.

## 7. Stage 5: Drawing Review

Use `BID_INTAKE_AND_DRAWING_REVIEW_CHECKLIST.md`.

Review drawings for:

- Scope limits.
- Demolition.
- Utilities.
- Roadworks.
- Asphalt.
- Concrete.
- Drainage.
- Waterworks.
- Sanitary.
- Electrical / lighting.
- Traffic control.
- Landscaping.
- Environmental controls.
- Details and standard drawings.
- Conflicts and missing information.

Outputs:

- Scope breakdown.
- Drawing-risk notes.
- Constructability issues.
- RFI list.
- RFQ package requirements.

## 8. Stage 6: Municipal Standards Review

Use `MUNICIPAL_STANDARDS_CHECKLIST.md`.

Confirm:

- Applicable municipality or AHJ.
- MMCD edition and supplement.
- Standard drawings.
- Approved materials.
- Permit requirements.
- Restoration requirements.
- Testing frequencies.
- Traffic-control requirements.
- ESC/environmental requirements.
- Closeout requirements.

Outputs:

- Cost impacts.
- Schedule impacts.
- Permit allowance.
- Testing allowance.
- Traffic-control allowance.
- Bid qualifications.

## 9. Stage 7: Quantity Takeoff

Takeoff should separate:

- Tender schedule quantities.
- Measured quantities.
- Self-perform quantities.
- Subcontract quantities.
- Supplier material quantities.
- Allowance items.
- Optional or provisional items.

Minimum takeoff categories:

- Mobilization.
- Removals.
- Excavation.
- Trenching.
- Pipe.
- Structures.
- Backfill.
- Granular base.
- Asphalt.
- Concrete.
- Traffic control.
- Testing.
- Landscaping.
- Disposal.

Outputs:

- Takeoff workbook.
- Measurement notes.
- Quantity risk notes.
- Estimate-ready quantity table.

## 10. Stage 8: RFQ Packaging

Use `RFQ_AUTOMATION_SPEC.md`.

Generate RFQs for required categories:

- Pipe / utility materials.
- Manholes and catch basins.
- Aggregates.
- Asphalt.
- Concrete.
- Traffic control.
- Testing.
- Coring and sawcutting.
- Pavement markings.
- Electrical / street lighting.
- Trucking and disposal.
- Landscaping.

RFQ process:

1. Select active suppliers by category.
2. Check preferred suppliers.
3. Attach relevant drawings/specs.
4. Generate email drafts.
5. Save drafts for review.
6. Update RFQ log.
7. Monitor replies.
8. Save quotes.
9. Update supplier master.

Outputs:

- RFQ emails.
- RFQ log.
- Supplier quote folder.
- Subcontractor quote folder.
- Supplier status updates.

## 11. Stage 9: Estimate Build

Use `ESTIMATE_ENGINE_ARCHITECTURE.md`.

Build estimate from:

- Quantity takeoff.
- Production rates.
- Labour rates.
- Equipment rates.
- Material pricing.
- Supplier quotes.
- Subcontractor quotes.
- Indirect costs.
- Municipal standards cost impacts.
- Risk allowances.
- Overhead.
- Profit.

Outputs:

- Estimate workbook.
- Estimate summary.
- Unit-price table.
- Risk register.
- Assumptions and exclusions.
- Bid strategy notes.

## 12. Stage 10: Bid Review

Before submission, review:

- Tender form completeness.
- Schedule of prices.
- Addenda acknowledgement.
- Required attachments.
- Bonding and insurance.
- WorkSafeBC.
- Subcontractor list.
- Methodology, if required.
- Construction schedule, if required.
- Assumptions and exclusions.
- Final price.
- Cash-flow exposure.
- Risk register.

Bid review result:

```text
READY TO SUBMIT / NEEDS FIX / DO NOT SUBMIT
```

## 13. Stage 11: Submission

Submission rules:

- Submit early enough to avoid portal issues.
- Save the exact submitted package.
- Save confirmation receipt.
- Record submitted price.
- Record submission date and time.
- Record person who submitted.

Save final documents in:

```text
11_Submission/
```

## 14. Stage 12: Post-Bid Review

After close, collect:

- Bid results.
- Low bidder.
- Iron House ranking.
- Spread to low bidder.
- Supplier quote performance.
- Estimate misses.
- Scope gaps.
- Productivity assumptions to adjust.
- Lessons learned.

Save in:

```text
12_Post_Bid/
```

Outputs:

- Post-bid review note.
- Updated production rates.
- Updated supplier competitiveness.
- Updated bid/no-bid rules.

## 15. Stage 13: Award Handoff

If awarded, create handoff package in:

```text
13_Award_Handoff/
```

Include:

- Contract documents.
- Award letter.
- Final estimate budget.
- Supplier quotes used.
- Subcontractor quotes used.
- Assumptions and exclusions.
- Project risks.
- Permits required.
- Submittals required.
- Testing requirements.
- Traffic requirements.
- ESC requirements.
- Startup checklist.

Output:

```text
Construction-ready startup package
```

## 16. System Feedback Loops

Iron House OS must improve after every bid.

Update:

- Supplier master.
- Supplier response rates.
- Supplier pricing competitiveness.
- Production rates.
- Equipment assumptions.
- Labour assumptions.
- Bid/no-bid rules.
- Municipal standards notes.
- RFQ templates.
- Estimate templates.

## 17. Minimum Phase 1 Workflow

Phase 1 should support:

1. Create project folder manually from standard.
2. Complete bid intake checklist.
3. Complete municipal standards checklist.
4. Complete quantity takeoff manually.
5. Generate RFQ drafts manually or semi-automatically.
6. Build estimate workbook manually.
7. Save final submission package.
8. Record post-bid results.

## 18. Future Automation Workflow

Later phases should automate:

- Tender discovery.
- Opportunity scoring.
- Folder creation.
- Document download.
- Addenda tracking.
- Drawing sheet classification.
- Quantity extraction assistance.
- RFQ draft generation.
- Gmail quote monitoring.
- Quote extraction.
- Estimate workbook generation.
- Bid calendar reminders.
- Post-bid analytics.
