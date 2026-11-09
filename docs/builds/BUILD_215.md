# Build 215 — Production-candidate cutover package

Build 215 completes the pre-infrastructure release package.

- `scripts/release_candidate_evidence.py` produces JSON and Markdown evidence bound to the exact Git commit/tree and SHA-256 hashes of deployment, smoke, backup, restore, and operator-runbook inputs.
- Release readiness generates and retains the evidence bundle only after its disposable production-stack smoke and recovery drill succeeds.
- The cutover checklist defines prerequisites, execution order, verification, and abort conditions.
- The operator acceptance record remains pending until a real, explicitly approved cutover.

This build validates a production candidate. It does not select or provision a host, change DNS, buy services, configure external alert delivery, send communications, or authorize live traffic.
