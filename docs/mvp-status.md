# Iron House OS MVP Status

## Current status

IHOS is now an internal web-app MVP scaffold with connected modules for project setup, documents, takeoff, estimating, RFQ drafting, bid packaging, and readiness checks.

## Working backend path

- Projects can be created and opened.
- Takeoff engine can generate and summarize quantities.
- Takeoffs can be saved to project records.
- Estimate handoff can convert takeoff quantities into estimate lines.
- Estimate workspaces can be saved to project bid records.
- RFQ package drafts can be generated from takeoff/estimate items.
- Project readiness can check minimum bid workflow completion.
- System readiness reports enabled MVP services.

## Working frontend path

- Project workspace exists.
- MVP workflow page exists.
- Takeoff engine panel exists.
- Estimate workspace panel exists.
- RFQ linkage panel exists.
- Project readiness panel exists.

## Needs fast MVP work

1. Wire new panels into the project workspace tabs.
2. Add real file upload/storage for drawings and tender documents.
3. Review database schema/migrations against current SQLAlchemy models.
4. Run CI and fix any lint/test failures.
5. Harden authentication and permissions before external exposure.
6. Add end-to-end browser smoke testing.

## Defer

- Background agents.
- Gmail auto-send.
- Google Drive sync.
- AI vector drawing takeoff.
- Field mobile app.
- Accounting integrations.
- Full supplier scraping automation.

## Recommended first live use

Use IHOS as an estimator-controlled assistant for the first live bid. Keep estimator review mandatory for all quantities, pricing, RFQs, assumptions, exclusions, and final bid output.
