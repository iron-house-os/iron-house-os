# Build 225 — Crew scheduling and time-off workflow

## Outcome

Iron House OS now provides a role-scoped scheduling workflow across the Foreman, Operator, and Employee portals.

## Delivered

- Foremen can publish a job shift to one or more selected employees with date, start/end time, meeting point, and instructions.
- Employees and operators see only their own scheduled shifts.
- Employees and operators can submit dated time-off requests with comments.
- Management can approve or decline pending requests and retain decision notes and audit timestamps.
- Viewer accounts cannot schedule crews, create another employee's records, or submit another employee's time.
- Schedule and time-off tools have dedicated dashboard workspaces without changing the locked Iron House visual baseline.

## Data and privacy boundary

This build stores operational schedule and request information only. It does not add SIN, banking, medical, or payroll data.

## Verification

- Backend scheduling, approval, date-validation, and denial tests.
- Full backend suite.
- Frontend unit tests and production TypeScript/Vite build.
- Visual design lock and release gates.
