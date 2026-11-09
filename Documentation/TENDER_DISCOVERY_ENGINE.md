# Tender Discovery Engine

This specification defines how Iron House OS discovers, scores, stores, and prioritizes civil construction opportunities.

## Goals
- Search BC and municipal tender sources daily.
- Filter for work that matches Iron House capabilities.
- Create a standardized opportunity record.
- Trigger project folder creation for approved opportunities.

## Primary Sources
- BC Bid
- CivicInfo BC
- Municipal procurement portals
- Regional districts
- School districts
- Utilities, ports, and transportation agencies

## Opportunity Record
Each record should capture:
- Project name
- Owner
- Tender number
- Closing date/time
- Mandatory meeting
- Estimated value (if published)
- Location
- Scope summary
- Download links
- Addenda count
- Status (New, Reviewing, GO, NO-GO, Submitted, Awarded, Lost)

## Scoring Factors
Projects should receive weighted scores for:
- Civil scope fit
- Geographic fit
- Estimated contract size
- Self-perform percentage
- Bonding requirements
- Traffic complexity
- Environmental complexity
- Competition risk
- Schedule compatibility
- Working capital requirements

## Automation Flow
1. Search sources.
2. Detect new opportunities.
3. Deduplicate.
4. Download available documents.
5. Create project folder using PROJECT_FOLDER_STANDARD.
6. Queue bid intake checklist.
7. Notify user of high-scoring projects.

## Phase 1
- Manual review of discovered opportunities.
- Standard opportunity tracker.
- Basic scoring.
- Links to downloaded documents.

## Future
- Automatic download of bid packages.
- AI-assisted scope classification.
- Historical owner analytics.
- Win-rate tracking.
- Calendar integration.
- One-click project creation.
