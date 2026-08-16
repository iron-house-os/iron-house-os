# Worker orientation deployment controls

## Purpose

Iron House OS stores append-only company and project/site orientation evidence for each onboarding record. The workflow supports the topics in WorkSafeBC OHS Regulation 3.23, additional-orientation triggers under section 3.24, and retained training history under section 3.25. It records evidence; it does not make an automatic legal-compliance conclusion.

## Deployment states

- **Blocked** — company orientation is absent, incomplete, or competency is not passed.
- **Supervised work only** — company orientation is complete for a field worker, but the current site orientation is absent, incomplete, or competency is not passed.
- **Ready** — required company evidence is complete and, for field staff, site evidence is complete; PPE and qualifications are verified, the worker has acknowledged the record, and competency is passed.

Activation fails closed unless the computed status is **Ready**. A changed site, hazard, task, observed unsafe performance, worker request, qualification expiry, or refresher creates a new orientation record rather than replacing history.

## Deployment sequence

1. Apply Alembic migration `20260816_0018`.
2. Confirm `worker_orientations` is present and system readiness reports the current migration.
3. Validate in staging with a controlled test worker: Blocked, Supervised work only, then Ready.
4. Export the test worker's CSV and verify worker, site, trigger, instructors, topics, dates, versions, results, acknowledgement and evidence.
5. Obtain the required owner approval before any production deployment. Do not bypass the protected GitHub production environment reviewer.

No production configuration, credentials, records, or infrastructure are changed by this implementation.
