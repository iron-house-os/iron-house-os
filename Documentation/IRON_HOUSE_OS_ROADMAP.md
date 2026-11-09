# Iron House OS Roadmap

## Purpose

Iron House OS is the operating system for building, estimating, bidding, supplier management, RFQ workflows, field execution, and business administration for Iron House civil construction work.

The goal is to turn the current bidding and supplier workflow into a repeatable system that can:

- Review tender packages and drawings.
- Extract quantities and scope.
- Apply Iron House execution assumptions.
- Build bid workbooks.
- Build RFQ packages.
- Track suppliers, pricing, and responses.
- Produce client-ready bid documents.
- Support field schedules, procurement, and project closeout.

## Current Operating Assumptions

Unless overridden for a specific project, Iron House estimating should assume:

- Self-perform excavation, trenching, pipe installation, manholes, catch basins, backfill, compaction, subgrade preparation, granular base/sub-base, topsoil, cleanup, and general earthworks.
- Use rented equipment in the early phase.
- Small in-house crew model.
- Subcontract concrete formwork and finishing, fine grading for asphalt, asphalt paving, pavement markings, street lighting, electrical, specialty traffic systems, hydro-vac, coring, testing, and other specialty scopes.
- Add company overhead, startup cost recovery, truck/equipment burden, supervision, administration, insurance, bonding, and contingency.

## Default Supplier Preferences

Use these defaults unless project-specific pricing or direction overrides them:

| Scope | Default Supplier / Subcontractor |
|---|---|
| PVC pipe | EMCO |
| Ductile iron | EMCO |
| Catch basins | Amrize |
| Manholes | Amrize |
| Asphalt | Superior Paving |
| Testing | Advanced Testing |
| Concrete | JWS |
| Coring | Performance Coring |

## Roadmap Phases

## Phase 1 — Foundation System

### Objective
Create the core repository structure and base documentation needed for repeatable Iron House workflows.

### Deliverables

- Repository folder structure.
- Roadmap documentation.
- Bid workflow documentation.
- Supplier/RFQ workflow documentation.
- Estimating assumptions documentation.
- File naming standards.
- Basic project folder template.

### Status
In progress.

### Target Folders

```text
Documentation/
Templates/
Estimating/
RFQ/
Suppliers/
Projects/
Scripts/
Branding/
Forms/
```

## Phase 2 — Bid Build Engine

### Objective
Create a repeatable estimating engine that can turn drawings and tender documents into a structured bid workbook.

### Deliverables

- Estimate workbook template.
- Standard cost codes.
- Quantity takeoff structure.
- Scope review checklist.
- Drawing review checklist.
- Municipal standards checklist.
- Risk/clarification log.
- Bid summary sheet.
- Markup, overhead, profit, and contingency logic.

### Core Workflow

1. Intake tender documents.
2. Identify project location, owner, engineer, closing date, bonding requirements, and mandatory documents.
3. Review drawings and specifications.
4. Extract scope by discipline.
5. Build quantity takeoff.
6. Apply production rates and supplier/subcontractor pricing.
7. Add rentals, labour, trucking, disposal, testing, traffic control, permits, and overhead.
8. Build final bid summary.
9. Produce submission checklist.

## Phase 3 — RFQ Package Builder

### Objective
Create a repeatable system for sending supplier and subcontractor RFQs with the correct attachments and scope notes.

### Deliverables

- Supplier master workbook.
- RFQ email templates.
- Supplier category map.
- Attachment checklist.
- Scope-specific RFQ packages.
- Follow-up email templates.
- Response tracking sheet.

### RFQ Categories

- Pipe and fittings.
- Manholes and catch basins.
- Aggregates.
- Asphalt paving.
- Concrete subcontractors.
- Coring.
- Testing.
- Traffic control.
- Pavement markings.
- Street lighting/electrical.
- Landscaping and restoration.
- Specialty subcontractors.

## Phase 4 — Supplier Database Expansion

### Objective
Build a strong BC civil construction supplier network with categorized, verified, and usable contact information.

### Deliverables

- Supplier list with at least 100 useful contacts.
- Category tags.
- Region tags.
- Email verification notes.
- Supplier status field.
- Preferred supplier flag.
- Pricing history.
- RFQ response history.

### Supplier Status Values

- Preferred.
- Active.
- New lead.
- Needs verification.
- Bad email.
- No account / pricing restricted.
- Do not use.

## Phase 5 — Tender Monitoring

### Objective
Create a daily tender search workflow for manageable civil construction opportunities in BC.

### Target Sources

- BC Bid.
- CivicInfo BC.
- Municipal procurement pages.
- School district procurement pages.
- Regional district procurement pages.
- Crown corporation procurement pages.
- Other BC public-sector tender portals.

### Deliverables

- Tender search checklist.
- Bid/no-bid scoring model.
- Opportunity tracker.
- Region and scope filters.
- Tender intake folder standard.
- Summary template for recommended opportunities.

## Phase 6 — Municipal Standards Engine

### Objective
Ensure bid reviews account for supplementary municipal standards that affect cost, schedule, approved materials, inspection, testing, traffic control, ESC, temporary works, and restoration.

### Deliverables

- Municipality standards checklist.
- MMCD supplement tracking.
- Approved materials list tracker.
- Inspection/testing requirement tracker.
- Pavement restoration requirement tracker.
- Traffic control and permit tracker.
- Environmental and tree protection tracker.

## Phase 7 — Field Execution System

### Objective
Connect estimating assumptions to actual field execution.

### Deliverables

- Daily field report template.
- Crew and equipment planning sheet.
- Lookahead schedule template.
- Material order tracker.
- Subcontractor coordination checklist.
- Deficiency log.
- Change order log.
- Photo documentation standard.

## Phase 8 — Business Operations

### Objective
Support year-one Iron House operations with simple tools for cash flow, startup costs, equipment planning, and company administration.

### Deliverables

- Startup cost tracker.
- Equipment rental vs ownership tracker.
- Truck burden calculator.
- LOC/cash-flow planning workbook.
- Insurance/bonding tracker.
- Admin checklist.
- Year-one growth plan.

## Phase 9 — App / Interface Layer

### Objective
Create a desktop, tablet, and mobile-friendly interface for Iron House OS.

### Requirements

- Works on desktop, tablet, iPhone, Android, and PC.
- Can be updated without rebuilding the entire system.
- Supports QR codes for quick access.
- Can link to Drive/GitHub-based source files.
- Simple enough for field and office use.

### Deliverables

- App structure plan.
- Navigation map.
- QR code strategy.
- Mobile-friendly forms.
- Dashboard concept.
- Update workflow.

## Priority Build Order

1. Repository documentation and folder structure.
2. Estimating assumptions and bid workflow.
3. Supplier master and RFQ package builder.
4. Estimate workbook templates.
5. Tender monitoring workflow.
6. Municipal standards checklist.
7. Field execution templates.
8. Business operations workbooks.
9. App/interface layer.

## Near-Term Task List

- Create base documentation files.
- Create estimating assumptions document.
- Create bid workflow document.
- Create RFQ package builder document.
- Create supplier master schema.
- Create project folder template.
- Create standard bid checklist.
- Create municipal standards checklist.
- Create first version of estimate workbook template.
- Create first version of opportunity tracker.

## Definition of Done

A phase is complete when:

- Required files exist in the repo.
- Workflow is documented clearly enough to repeat.
- Templates are usable without rebuilding from scratch.
- Naming conventions are consistent.
- The system supports real Iron House bid work.
- Next-step actions are clear.

## Operating Rule

This repository should stay practical. Every file should help Iron House estimate, bid, procure, build, track, or administer real civil construction work.
