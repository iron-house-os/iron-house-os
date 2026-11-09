# IHOS Operator Runbook

## Daily startup

1. Start the backend, frontend, and database.
2. Open `/readiness` and confirm status is `ready`.
3. Open the frontend dashboard.
4. Create or select the active bid project.
5. Use the MVP Workflow page to move through the project.

## Bid workflow

1. Create project.
2. Register tender documents and drawings.
3. Run quantity takeoff.
4. Save takeoff to the project.
5. Send estimate-ready items to estimating.
6. Save the estimate workspace.
7. Generate RFQ drafts.
8. Check project readiness.
9. Build final bid package.

## Recovery

- If readiness fails, check backend logs first.
- If frontend cannot connect, verify `VITE_API_BASE_URL`.
- If project data is missing, verify database connection and migrations/schema.
- If RFQ drafts are missing, verify takeoff or estimate source items have categories and descriptions.

## First-live-use rule

Use IHOS as a bid assistant until the first full bid has been reconciled manually. Do not rely on automated quantities or pricing without estimator review.
