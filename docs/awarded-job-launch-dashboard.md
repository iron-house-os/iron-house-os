# Awarded-job launch dashboard

## Purpose

The project workspace gives management and estimators one read-only launch view after a project is awarded. The dashboard connects the generated job number and project-start checklist to the estimate, baseline budget, purchase-order requests, safety records, and project documents.

The dashboard does not copy or own those source records. It derives the current summary from each operational register so the figures cannot drift from the records they represent.

## Access and scope

- The dashboard is available only for awarded projects with a job number.
- Administrators, operations managers, and estimators can read it.
- Employee/viewer accounts cannot read the management launch summary.
- Every count and total is filtered to the selected project.

## Readiness rule

Mobilization readiness is determined only by the ten-item awarded-job start checklist. Estimate, budget, PO, safety, and document values are indicators and never create or imply an approval.

The next incomplete checklist control is shown so management has one clear next action. When all ten controls are checked, the dashboard reports the job as ready. Source documents, permits, engineering approvals, and project-specific evidence remain required where applicable.

## Derived indicators

- estimate workspace count and whether a priced estimate exists;
- active baseline-budget total and entry count (void entries excluded);
- project PO-request count and pending-approval count;
- counts for project safety permits, emergency cards, hazard assessments, toolbox talks, and corrective actions;
- blocked safety-launch status, requirement count, internal folder status, portal-access status, and assignment count; and
- project document count.

The safety-launch indicators are setup controls, not safety evidence. `blocked` with zero project safety records and portal status `not_started` means that project-specific verification and assignments still require authorized human action.

Direct links preserve the project ID and name when opening Estimating, Finance, PO Requests, Safety Operations, or Documents.
Confidential incident and first-aid occurrence counts are deliberately excluded from the estimator-visible launch summary.

## API

`GET /api/v1/projects/{project_id}/launch-dashboard`

The endpoint returns `409` when the project has not been awarded, `403` for a role without management/estimating access, and `404` when the project does not exist.
