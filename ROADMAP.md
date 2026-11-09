# Iron House OS Roadmap

## Product Objective

Iron House OS is an internal civil construction operating system for finding tenders, reviewing tender packages, organizing suppliers, generating RFQs, comparing quotes, building estimates, and assembling bid packages.

## Current Completed Core

- Dashboard
- Project Workspace command center
- Supplier Database
- RFQ Builder
- Quote Comparison
- Tender Tracker
- Document Library
- Estimate Engine v2
- Drawing Intelligence Core
- Build Agent / Foreman v1
- Autonomous Dispatcher v1

## Next Product Builds

### Build 25 — Quantity Takeoff Engine v1

Create a structured quantity register that can accept detected quantities from drawings or manual estimator entry.

Initial scopes:

- Pipe lengths
- Manholes
- Catch basins
- Hydrants
- Valves
- Fittings
- Asphalt areas
- Concrete quantities
- Curb and sidewalk quantities

### Build 26 — Municipality Intelligence v1

Create a municipal standards checker that flags cost-impacting supplementary requirements.

Initial municipalities:

- Surrey
- Vancouver
- Burnaby
- Richmond
- Delta
- Langley
- Abbotsford
- Chilliwack

### Build 27 — RFQ Automation v1

Generate project-scoped RFQ packages from estimate scopes and quantity registers.

### Build 28 — Bid Package Generator v1

Assemble a reviewable bid package including assumptions, exclusions, schedule, price, and RFQ backup.

## Autonomous Development Objective

The development system should increasingly reduce manual prompting by allowing a Foreman to:

1. Read this roadmap.
2. Read the structured backlog.
3. Select the highest-priority open task.
4. Produce an implementation plan.
5. Optionally call a configured coder command.
6. Run checks.
7. Prepare reviewable output.

The system must never submit bids, send emails, spend money, merge pull requests, approve contracts, or make external commitments without explicit human approval.
