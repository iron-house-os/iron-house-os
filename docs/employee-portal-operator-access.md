# Employee Portal operator access

Employee Portal and Foreman Portal are the only workforce entry points. Operator tools are a labelled section inside Employee Portal. Foreman Portal remains separate because it contains supervisory scheduling, crew approvals, safety release, and production controls.

## Server-side authorization

Opening or seeing the operator section does not authorize equipment operation. IHOS enables operator actions only when all of these stored controls are present for the signed-in employee:

1. The employee profile is active.
2. An active onboarding record remains linked to the employee.
3. IHOS computes the onboarding deployment status as `Ready`, including recorded company/site orientation, PPE, qualification verification, worker acknowledgement, and passed competency evidence.
4. Management has approved an operator-track milestone only after its written assessment and observed practical assessment both passed.
5. An operational equipment or vehicle record is currently assigned to that employee.

The operator-track milestone is an internal IHOS development and competency control. It does not replace a regulated certificate, supervisor verification, site-specific instruction, task hazard assessment, permit, or current-condition decision.

Operator time requires at least one current assignment. Machine inspections and assigned-equipment job photos are restricted to the employee's current equipment. Operator load tracking is restricted to the current equipment or vehicle selected in the record. Direct API requests receive the same checks as the portal.

## Management assignment controls

Administrators and operations managers can assign an active employee from the Equipment register or Vehicle Tracking. Assignment is deliberately only one gate: assigning a machine never fills in, infers, or fabricates orientation, PPE, qualification, competency, or acknowledgement evidence.

Removing the assignment, making the employee inactive, placing the resource out of operational service, losing deployment readiness, or lacking approved operator qualification evidence makes operator access fail closed.

## Route compatibility

Existing `/operator` and `/operator-portal` links redirect into `/employee-portal/operator`. Legacy links for general employee functions such as schedule, receipts, backups, and small-equipment inspections redirect to their Employee Portal sections. No standalone Operator Portal navigation entry remains.
