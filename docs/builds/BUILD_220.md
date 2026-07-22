# Build 220 — Field Operations Foundation

## Outcome

Build 220 establishes one connected field-operations data layer and usable portal routes while preserving the approved Iron House visual baseline.

## Included

- Vehicle tracking seeded with Mac Warren’s GMC 3500 Truck 001 and Jeremie Peters’ GMC 3500 Truck 002.
- Fuel, kilometre, maintenance, inspection and repair logs with multiple receipt/photo attachments.
- Employee contact, emergency-contact, position, portal-role and course-ticket records. SIN, banking, medical and payroll data remain excluded.
- Cost-coded employee, operator and Foreman crew time linked to projects.
- Foreman Portal for journals, weather, materials/quantities, subcontractors, rental equipment, expenses, missing forms, production photos and daily hazard assessments.
- Operator Portal for time, machine inspections, issue severity, job photos, time-off and performance-review requests.
- Employee Portal for time, journal, photos, expenses, missing forms, requests, safety resources, employee details and ticket status.
- Medium, high and critical field issues automatically route to Jeremie Peters and Mac Warren in the internal alert queue.
- Weekly WorkSafeBC toolbox talk content, crew selection and individual digital acknowledgement.
- Database migration 20260722_0005, new API routes, permission coverage and regression tests.

## Validation

- Backend: 117 tests passed.
- Frontend: 21 tests passed.
- Frontend production build passed.
- Iron House visual-design lock passed with all 13 protected files unchanged.

## Next

Build 221 connects live project workbook materials and estimated quantities to installed-to-date Foreman production tracking.
