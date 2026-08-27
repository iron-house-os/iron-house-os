# Bennett estimate-to-quote shared-staging pilot

## Objective

Prove the issue #268 saved-estimate to customer-quote handoff against the authenticated shared-staging stack using the controlled Bennett source context from issue #314.

## Current scope

The pilot is intentionally draft-only. Human merge of Build 225 authorized the shared-staging data plan recorded in `ops/staging-pilots/2026-08-27-bennett-draft-pilot.json`, but GitHub rejected run `33110981733` before any job or data action because `runner.temp` is unsupported in job-level `env`. Build 226 repaired the workflow and run `33112675388` created the opportunity and immutable estimate workspaces, then blocked before quote creation because the staging Secure session cookie could not be sent over the tool's HTTP loopback origin. Human merge of the exact Build 227 repair authorizes the same bounded proof to resume through the live HTTPS staging origin.

The workflow:

1. waits for the exact merged release to deploy successfully to staging;
2. verifies live staging reports that exact release;
3. dry-runs and applies the immutable `2026-08-27-final` Bennett estimate source;
4. repairs only the exact legacy `STAGE-BENNETT-2026` marker while the project remains an opportunity;
5. authenticates through the IHOS session endpoint;
6. creates or reuses the concrete draft quote from the exact saved estimate workspace;
7. repeats the conversion and proves the quote ID does not change;
8. verifies subtotal $36,266.67, GST $1,813.33, and total $38,080.00;
9. verifies the project and quote remain unapproved, unissued, unaccepted, unawarded, and without a job number; and
10. uploads the release, import, and pilot reports as a 90-day GitHub Actions artifact.

## Approval boundary

This workflow must not approve, issue, accept, or send a quote; award a project; allocate a job number; or mutate production. The authenticated award/job-number proof remains a separate explicit management approval gate after the draft evidence is reviewed.

## Failure controls

The pilot fails closed when:

- staging is not on the exact current `main` release;
- multiple Bennett projects or final-revision workspaces exist;
- the project has left opportunity status;
- any non-empty project number remains;
- a final-revision workspace differs from its immutable approved source;
- money, source provenance, quote state, or retry identity differs from the expected record; or
- any approval, issuance, acceptance, award, or job-number evidence appears.
