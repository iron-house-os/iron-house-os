# Bennett staging award transition

## Objective

Convert the exact verified Bennett concrete quote draft into one awarded staging job after explicit management acceptance, without external issuance or production mutation.

## Approval and scope

Build 227 created and verified `Q-2026-002` in shared staging. On 2026-08-28, after the handoff identified explicit management acceptance or award as the next gate, Jeremie Peters replied **Accepted**.

The Build 228 workflow is therefore limited to:

- the exact Bennett opportunity, concrete estimate workspace, and quote recorded in `ops/staging-pilots/2026-08-28-bennett-award-transition.json`;
- the existing authenticated management acceptance endpoint;
- one permanent `IHYYYYNNN` job number with no hyphens;
- idempotent initialization and verification of the award pricing baseline, draft procurement plan, project workspace, start checklist, and launch dashboard;
- immutable staging evidence retained for 90 days.

It does not issue or send the quote, create procurement commitments, or mutate production.

## Execution gate

The workflow runs only after a human merges the exact Build 228 pull request and that exact release deploys successfully to staging. It fails closed on release drift, record drift, value drift, prior external issuance, an unexpected job number, duplicate allocation, or unsafe downstream controls.
