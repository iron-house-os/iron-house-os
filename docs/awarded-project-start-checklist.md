# Awarded project start checklist

IHOS creates one pre-populated project-start checklist when a project first becomes `awarded`. The checklist gives project management a consistent set of controls to confirm by selecting boxes instead of rewriting the startup requirements for every job.

## Standard controls

1. Award notice or executed contract and client scope record.
2. Scope, exclusions, allowances, and alternates review.
3. Current drawings, specifications, and addenda.
4. Project contacts, authority limits, and communication path.
5. Baseline budget and project cost codes.
6. Baseline schedule, milestones, and notice periods.
7. Subcontractor, material, equipment, and procurement plans.
8. Permit, insurance, and bonding assignments.
9. Project-specific safety and mobilization assignments.
10. Quality, inspection, testing, and as-built assignments.

## State and access

- Authenticated users with project write access can check or reopen an item.
- Every change stores the authenticated user's email and the change time.
- Readiness is derived: `ready` means all ten items are checked; otherwise the checklist is `not_ready`.
- Re-entering the awarded state does not duplicate the checklist or erase saved state.
- Opportunity and tendering projects do not receive a checklist. Existing legacy awarded projects are not backfilled automatically.

Project Workspace loads the checklist from `GET /api/v1/projects/{project_id}/start-checklist`. A selection is saved immediately through `PATCH /api/v1/projects/{project_id}/start-checklist/{code}`.

## Control boundary

A checked item records management confirmation only. It does not create or replace source documents, permits, contract approval, engineering approval, or project-specific safety evidence. Checklist provisioning does not create external folders, send notices, change contracts, or alter production data outside the normal deployment process.
