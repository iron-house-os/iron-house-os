# Iron House OS MVP Build Strategy

## Goal

Get an operating web app live as fast as possible.

The priority is not perfection. The priority is a usable system that helps Iron House manage tenders, suppliers, RFQs, estimates, quotes, documents, and bid packages from one place.

## Build Philosophy

Build working workflows first. Add deeper automation later.

Default approach:

1. Use simple forms before complex automation.
2. Use manual entry before AI extraction.
3. Use database records before integrations.
4. Use downloadable files before cloud-drive automation.
5. Use draft emails before automatic sending.
6. Use practical defaults before perfect configuration.
7. Push working vertical slices over broad unfinished modules.

## Approval Boundaries

The system can draft, calculate, organize, and recommend.

It must ask before:

- Sending external emails
- Submitting bids
- Spending money
- Signing or approving contracts
- Making binding commitments

## MVP Vertical Slices

### 1. Project Intake

Working app must create and track projects/tenders with:

- Project name
- Owner/client
- Municipality
- Bid due date
- Status
- Notes
- Linked documents

Deep tender scraping can come later.

### 2. Supplier Database

Working app must track suppliers with:

- Company name
- Category
- Service area
- Website
- Contact email
- Status notes

Automated supplier scraping can come later.

### 3. RFQ Builder

Working app must create RFQ packages with:

- Project
- Scope summary
- Due date
- Supplier recipients
- Required documents
- Draft RFQ email

Gmail sending can come later.

### 4. Estimate Engine

Working app must calculate:

- Line item cost
- Labour
- Equipment
- Materials
- Disposal
- Subcontract
- Indirects
- Risk
- Contingency
- Bonding
- Insurance
- Overhead
- Profit
- Final bid price

Advanced takeoff extraction can come later.

### 5. Quote Comparison

Working app must compare supplier quotes by:

- Line item
- Scope
- Supplier
- Amount
- Selected quote
- Reason if not lowest

Full RFQ email parsing can come later.

### 6. Workbook Export

Working app must export estimate workbooks.

Google Drive auto-save can come later.

## Defer Until After MVP

- Full AI drawing takeoff
- Municipality standards intelligence automation
- Gmail auto-send
- Google Drive deep sync
- Slack integration
- Background agents
- Mobile employee/employer apps
- Advanced dashboards
- Accounting integrations
- QR code app deployment

## Current Active Build Queue

1. Stabilize backend dependencies and basic tests
2. Finish RFQ package builder core workflow
3. Finish supplier database core workflow
4. Finish project intake core workflow
5. Connect quote comparison into estimating
6. Add simple dashboard cards
7. Add deployment readiness docs

## Operating Instruction

Keep moving task to task. Do not wait for new prompts unless a tool blocks, a file cannot be accessed, or approval is required.
