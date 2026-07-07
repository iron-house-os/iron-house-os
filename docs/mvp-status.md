# Iron House OS MVP Status

## Current MVP Readiness

Iron House OS is closer to a working web app than a pure scaffold. Several vertical slices already exist.

## Working / Mostly Working

### Project Workspace

Status: MVP-ready foundation

Capabilities:

- Create projects
- Filter projects by status
- View project detail dashboard
- Update status
- Archive projects
- See linked workspace tabs for RFQs, documents, suppliers, drawings, estimating, and activity

### Supplier Database

Status: MVP-ready foundation

Capabilities:

- Create suppliers
- Search suppliers
- Filter by category
- View supplier detail
- Update supplier profile
- Replace estimating contacts

### RFQ Builder

Status: MVP-ready foundation

Capabilities:

- Create RFQ packages
- List RFQ packages
- Read RFQ packages
- Select supplier recipients
- Register required documents
- Check RFQ readiness
- Generate single supplier RFQ draft text

### Estimating

Status: MVP-ready foundation

Capabilities:

- Load production rate library
- Add line items
- Use production activity defaults
- Enter direct unit costs
- Add mobilization and risk allowance
- Calculate contingency, overhead, profit, bonding, insurance, and final bid
- Export estimate workbook

### Quote Comparison

Status: Backend foundation

Capabilities:

- Compare quotes by line item and scope
- Use lowest quote by default
- Respect manually selected quote
- Track reason for non-low selected quote
- Calculate selected-total delta from lowest-total

## Needs Fast MVP Work

1. Dashboard
   - Replace placeholder with simple operating dashboard cards.
   - Show counts for projects, suppliers, RFQs, tenders, and active estimates where available.

2. Quote comparison UI
   - Add a simple quote comparison panel or page.
   - Manual quote entry is enough for MVP.

3. Estimating UI completion
   - Add disposal input.
   - Add vendor quote input.
   - Add risk probability.
   - Show category breakdown.

4. Deployment readiness
   - Confirm backend and frontend dependency installs.
   - Document local launch and production deployment steps.

5. RFQ package draft expansion
   - Existing single-supplier draft is good enough for MVP.
   - Batch draft generation can wait.

## Defer

- Background agents
- Gmail auto-send
- Google Drive sync
- AI drawing takeoff
- Municipality standards automation
- Accounting integrations
- Mobile employee app
- Full supplier scraping automation

## Next Build Action

Build dashboard cards and MVP launch checklist next.
