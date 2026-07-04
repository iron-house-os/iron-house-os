# Project Folder Standard

This document defines the standard Iron House OS folder structure for every tender, estimate, RFQ package, bid submission, and post-bid handoff.

## 1. Purpose

Every project should be stored the same way so the OS can find drawings, specifications, addenda, supplier quotes, estimate workbooks, RFQ logs, bid forms, and post-bid records without manual searching.

This structure is designed for:

- Civil construction tender intake.
- Drawing and specification review.
- Quantity takeoff.
- Supplier and subcontractor RFQs.
- Estimate workbook creation.
- Bid submission.
- Post-bid tracking.
- Future project handoff if awarded.

## 2. Project Folder Naming

Use this format:

```text
[YYYY-MM-DD_CloseDate]_[Owner]_[ProjectCode]_[ShortProjectName]
```

Examples:

```text
2026-07-15_CityOfSurrey_WR26-012_MarineDriveParkingLot
2026-08-02_DistrictOfSechelt_EN27TBP003_TreeProtectionWorks
2026-07-29_TownshipOfLangley_LSI-03_FraserHighwayBikePath
```

Rules:

- Use the tender closing date first.
- Use short owner names.
- Keep project names readable.
- Avoid spaces where possible.
- Avoid special characters that cause file-sync problems.
- Keep the tender number or project code in the folder name.

## 3. Standard Folder Tree

```text
Project_Folder/
├── 00_Admin/
├── 01_Tender_Documents/
├── 02_Drawings/
├── 03_Addenda/
├── 04_Standards_and_Specs/
├── 05_Takeoff/
├── 06_Estimate/
├── 07_RFQs/
├── 08_Supplier_Quotes/
├── 09_Subcontractor_Quotes/
├── 10_Correspondence/
├── 11_Submission/
├── 12_Post_Bid/
├── 13_Award_Handoff/
└── 99_Archive/
```

## 4. Folder Details

### 00_Admin

Store administrative bid information:

- Bid summary sheet.
- Go/no-go review.
- Mandatory meeting notes.
- Site visit notes.
- Insurance requirements.
- Bonding requirements.
- WorkSafeBC requirements.
- Contact list.
- Submission instructions.

### 01_Tender_Documents

Store owner-issued tender documents:

- Instructions to bidders.
- Contract documents.
- Form of tender.
- Schedule of quantities.
- Supplementary conditions.
- Project-specific specifications.
- Tender forms.
- Appendices.

### 02_Drawings

Store all drawings:

- Civil drawings.
- Roadworks drawings.
- Utility drawings.
- Landscape drawings.
- Electrical drawings.
- Traffic management drawings.
- Demolition drawings.
- ESC drawings.
- Detail sheets.

Recommended subfolders:

```text
02_Drawings/
├── Current/
├── Superseded/
├── Extracted_Sheets/
└── Markups/
```

### 03_Addenda

Store addenda and Q&A:

- Addendum PDFs.
- Clarification notices.
- Owner Q&A.
- Revised drawings.
- Revised forms.
- Revised specifications.

Rules:

- Never overwrite original addenda.
- Save addenda using issue number and date.
- Move superseded drawings/specs into the superseded folder.

### 04_Standards_and_Specs

Store municipal and technical standards:

- MMCD references.
- Municipal supplementary specifications.
- Municipal standard drawings.
- Approved materials lists.
- Testing requirements.
- Traffic-control requirements.
- Environmental requirements.
- Permit requirements.

This folder should include the output of:

- `MUNICIPAL_STANDARDS_CHECKLIST.md`
- Relevant municipality standard references.

### 05_Takeoff

Store takeoff files:

- Quantity takeoff workbook.
- Measurement exports.
- PDF markups.
- Quantity notes.
- Cut/fill calculations.
- Asphalt area calculations.
- Pipe length summaries.
- Structure counts.
- Concrete quantity summaries.

Recommended naming:

```text
Takeoff_[ProjectCode]_v1.xlsx
Takeoff_[ProjectCode]_v2.xlsx
Takeoff_Notes_[ProjectCode].md
```

### 06_Estimate

Store estimate files:

- Estimate workbook.
- Estimate summary.
- Production-rate assumptions.
- Labour-rate assumptions.
- Equipment-rate assumptions.
- Material assumptions.
- Risk register.
- Assumptions and exclusions.
- Bid review notes.

Recommended naming:

```text
Estimate_[ProjectCode]_v1.xlsx
Estimate_[ProjectCode]_BidReview.pdf
Assumptions_Exclusions_[ProjectCode].md
Risk_Register_[ProjectCode].xlsx
```

### 07_RFQs

Store outgoing RFQ packages:

- RFQ email drafts.
- RFQ PDFs.
- Trade-specific drawing extracts.
- RFQ log.
- Attachment packages.

Recommended subfolders:

```text
07_RFQs/
├── Pipe_Utilities/
├── Structures/
├── Aggregates/
├── Asphalt/
├── Concrete/
├── Traffic_Control/
├── Testing/
├── Electrical_Lighting/
├── Landscaping/
└── Trucking_Disposal/
```

### 08_Supplier_Quotes

Store material supplier quotes:

- Pipe quotes.
- Structure quotes.
- Aggregate quotes.
- Miscellaneous material quotes.
- Price lists.
- Email exports.

Recommended subfolders:

```text
08_Supplier_Quotes/
├── Pipe_Utilities/
├── Structures/
├── Aggregates/
├── Concrete_Supply/
└── Misc_Materials/
```

### 09_Subcontractor_Quotes

Store subcontractor quotes:

- Asphalt.
- Concrete.
- Traffic control.
- Pavement markings.
- Testing.
- Coring / sawcutting.
- Electrical / street lighting.
- Landscaping.
- Trucking / disposal.

### 10_Correspondence

Store project communication:

- Owner emails.
- Consultant emails.
- Supplier emails.
- Subcontractor emails.
- RFIs.
- Clarifications.
- Meeting notes.
- Call notes.

Recommended subfolders:

```text
10_Correspondence/
├── Owner_Consultant/
├── Suppliers/
├── Subcontractors/
├── RFIs/
└── Internal_Notes/
```

### 11_Submission

Store final bid submission files:

- Completed tender form.
- Completed schedule of prices.
- Addenda acknowledgement.
- Bid bond or security.
- Consent of surety.
- Insurance documents.
- WorkSafeBC clearance.
- Subcontractor list.
- Methodology.
- Schedule.
- Final assumptions and exclusions.
- Final submitted PDF.
- Submission confirmation.

### 12_Post_Bid

Store post-bid records:

- Submitted price summary.
- Bid results.
- Competitor pricing.
- Quote comparison.
- Lessons learned.
- Post-bid follow-up notes.
- Debrief notes.

### 13_Award_Handoff

Use only if the project is awarded:

- Final contract.
- Award letter.
- Project startup checklist.
- Construction schedule.
- Approved submittals.
- Supplier purchase orders.
- Subcontractor agreements.
- Permits.
- Traffic management plan.
- Safety plan.
- ESC plan.
- Contact list.
- Approved estimate budget.

### 99_Archive

Store superseded or inactive material:

- Old estimate versions.
- Superseded drawings.
- Superseded RFQs.
- Cancelled bid material.
- Duplicate files.

## 5. Standard File Naming

Use this format:

```text
[DocumentType]_[ProjectCode]_[Description]_[YYYY-MM-DD]_v[#].[ext]
```

Examples:

```text
Estimate_WR26-012_MarineDrive_2026-07-04_v1.xlsx
RFQ_WR26-012_Asphalt_SuperiorPaving_2026-07-04.eml
Quote_WR26-012_Pipe_EMCO_2026-07-05.pdf
Takeoff_WR26-012_PipeQuantities_2026-07-04_v1.xlsx
RFI_WR26-012_UtilityConflict_2026-07-06.md
```

## 6. Version Control Rules

- Never overwrite owner-issued tender documents.
- Never delete original drawings.
- Move superseded files to `Superseded` or `99_Archive`.
- Use version numbers for internal working files.
- Use dates on external quotes and RFQs.
- Keep the final submission package separate from working files.
- Store the exact submitted package in `11_Submission`.

## 7. Required Project Index

Each project folder should include:

```text
PROJECT_INDEX.md
```

Minimum contents:

```text
# Project Index

Project:
Project Code:
Owner / Municipality:
Consultant:
Closing Date:
Bid Status:
Estimator:

## Key Files
Tender Documents:
Current Drawings:
Addenda:
Takeoff:
Estimate:
RFQ Log:
Submission:

## Key Risks
-

## Open RFIs
-

## Bid Qualifications
-
```

## 8. Automation Requirements

Iron House OS should eventually be able to:

- Create this folder tree automatically.
- Generate `PROJECT_INDEX.md` automatically.
- Save tender discovery files into the correct folders.
- Place drawings into `02_Drawings/Current`.
- Place addenda into `03_Addenda`.
- Place standards into `04_Standards_and_Specs`.
- Place RFQ drafts into `07_RFQs`.
- Place supplier replies into `08_Supplier_Quotes` or `09_Subcontractor_Quotes`.
- Place final bid files into `11_Submission`.
- Move superseded files to archive folders.

## 9. Minimum Phase 1 Implementation

Phase 1 should support:

1. Manual project folder creation from this standard.
2. Project index template creation.
3. Consistent RFQ and estimate file naming.
4. Manual placement of drawings and tender documents.
5. Manual archive of superseded files.
6. Consistent final submission storage.

## 10. Future Implementation

Later phases should support:

- Google Drive folder creation.
- GitHub-backed templates.
- Automatic tender download sorting.
- Automatic addenda tracking.
- Gmail attachment saving.
- Estimate workbook generation.
- RFQ package export.
- Award handoff folder generation.
