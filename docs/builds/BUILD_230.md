# Build 230 — AI Legal Control Centre

## Task card

- Owner: Iron House Administrator
- Environment: development only
- Status: Ready for review; production activation blocked
- Branch: `build-230-ai-legal-control-centre`
- Objective: create a supervised, source-controlled construction legal team inside Iron House OS.

## Verified

- Administrator-only legal matter register, 13-specialist triage roster and controlled authority register.
- Contract review and drafting support is routed through a server-side OpenAI Responses API boundary.
- AI output remains draft work product and must cite approved, active authority IDs.
- Personal-information and privilege-requested matters fail closed before AI processing.
- Deadlines are candidates until a human records verification evidence.
- Matter creation, analysis, deadline creation and deadline verification write durable legal audit events.
- The feature flag defaults off. This build does not deploy, merge or activate production.
- Credential-like development defaults were removed from application configuration; deployments continue to use environment-provided values.
- BC Construction Prompt Payment Act Parts 1–5 and sections 47–51 are recorded as not in force and are excluded from AI sources.

## Assumptions

- Phase 1 access is limited to the administrator.
- Initial jurisdiction is British Columbia, Canada.
- The tool supports internal issue spotting and lawyer-ready drafts; it does not replace retained counsel.
- Actual client contracts, employee information and privileged instructions are not committed as fixtures.

## Open items / activation blockers

- Retained BC construction counsel must approve the operating charter, disclaimer, escalation rules and contract templates.
- Privacy review must approve AI data handling, retention, deletion, vendor terms and privilege protocol.
- Security review must verify secrets, logging, backups, access control and incident response.
- Management must approve the source-revalidation owner and cadence.
- Production configuration, migration, smoke testing and release approval remain outstanding.

## Specialist team

1. Legal Intake & Privilege Coordinator
2. Construction Contracts Counsel Assistant
3. Builders Lien & Payment Analyst
4. Tender & Procurement Analyst
5. Subcontract & Supplier Analyst
6. Employment & Labour Analyst
7. WorkSafeBC & OHS Analyst
8. Corporate Governance Analyst
9. Privacy & AI Governance Analyst
10. Insurance & Risk Transfer Analyst
11. Claims, Disputes & Collections Analyst
12. Environmental & Heritage Analyst
13. Transportation & Fleet Compliance Analyst

## Controls

- No autonomous legal opinion, filing, notice, signature, settlement, waiver, discipline or termination action.
- No AI processing where the matter is marked personal information or privilege requested.
- Inactive or unapproved authorities cannot be cited by the AI.
- AI cannot verify its own deadlines.
- Production remains untouched and the feature defaults disabled.

## Test plan

- Backend Ruff and full pytest suite.
- Fresh Alembic migration.
- Frontend Vitest, TypeScript and production build.
- Secret scan, synthetic-fixture review and `git diff --check`.

## Authoritative sources

- [BC Builders Lien Act](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_97045_01)
- [BC Construction Prompt Payment Act](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/25024)
- [BC Employment Standards Act](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_96113_01)
- [BC Workers Compensation Act](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/19001_00_multi)
- [WorkSafeBC OHS Regulation Part 20](https://www.worksafebc.com/en/law-policy/occupational-health-safety/searchable-ohs-regulation/ohs-regulation/part-20-construction-excavation-and-demolition)
- [BC Personal Information Protection Act](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/03063_01)
- [BC Limitation Act](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/12013_01)
