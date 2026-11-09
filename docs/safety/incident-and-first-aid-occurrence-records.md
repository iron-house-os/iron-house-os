# Incident and first-aid occurrence records

Iron House OS stores incident, near-miss, and first-aid occurrence records in the authenticated Safety Operations workflow. These are operational records; they do not make regulatory, medical, causation, disciplinary, or return-to-work determinations.

## Incident and near-miss workflow

- Administrators, operations managers, and linked forepersons can submit an incident or near miss.
- New occurrences start as `reported` and notify the configured management recipients.
- Management records initial review evidence before moving an occurrence to `under_review`.
- Closure requires verification evidence. Status changes preserve the prior state, next state, actor, timestamp, and evidence.
- Estimator accounts cannot create, review, or receive incident details through the field-operations bootstrap.

## First-aid privacy boundary

- Only administrators and operations managers can create or view the company first-aid occurrence register.
- Linked workers can receive only first-aid records tied to their own employee profile. Forepersons cannot read first-aid details through the bootstrap.
- The record captures a minimum operational data set: worker, time, location, attendant, general nature, aid provided, recorded outcome, and optional operational follow-up.
- Do not enter diagnoses, unrelated health history, medical opinions, regulatory conclusions, or disciplinary findings.
- First-aid occurrence records are recorded evidence and do not use the incident closure workflow.

## Deployment and review

This change adds record types within the existing field-record table and does not require a database migration. Validate authorization tests and the mobile Safety Operations layout in staging before any production approval.
