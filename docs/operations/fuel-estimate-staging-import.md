# Issue #134 fuel-standard estimate revisions

This controlled workflow classifies the eight Drive candidates, rebuilds only the estimates that were active on 2026-08-19, and links the replacements to IHOS **staging only**. It never modifies production or the bytes of an existing Drive file.

## Candidate classification

| Candidate | Verified state | Action |
| --- | --- | --- |
| Fernie manhole repair | Closed 2026-08-14; proposal exists; submission unverified | Historical only; issue #132 owns intake |
| Braidwood C26-085 | Active at review; closes 2026-08-20 14:00 PT | Rebuilt and staged as provisional |
| T2026-017 | Closed 2026-07-16; no verified submission | Leave unchanged; obsolete/closed |
| Hillcrest | Closed 2026-08-13; tender draft/checklist incomplete | Leave unchanged; historical draft |
| Firehall Q26-335 | Closed 2026-08-18; checklist still open | Leave unchanged; historical draft |
| Cumberland ITT-2602 | Active at review; closes 2026-08-20 15:00 PT | Rebuilt and staged as provisional |
| Downes Road MOT | Closed 2026-07-29; submission not started | Leave unchanged; historical draft |
| Cassidys | Stored in an archived, not-awarded reference dataset | Leave unchanged; archive/control only |

## Controlled replacements

| Project | Baseline Drive ID | Replacement Drive ID | Old total | New total | Fuel litres | Fuel cost at CAD 2.50/L | Tender variance |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Braidwood C26-085 | `1zC0CKUizVFKEGutIKGv3mW-PyZspzlVz` | `18KxEAuCM87Cpph7yUq0prJ55FdWcfqSw` | $13,212,251.87 | $13,234,351.13 | 33,825.0 | $84,562.50 | $22,099.26 |
| Cumberland ITT-2602 | `1d6sRDMNPmHI6Cwaup6Zrlv4OuaD0oMhvqKEqXeRuF8Q` | `115TFp1JR8yOLPkFOOWtem12xGcuXvHoSXIF9EjFR0KY` | $5,123,740.00 | $5,130,802.50 | 14,125.0 | $35,312.50 | $7,062.50 |

The litre assumptions use current company equipment defaults over the full planned duration. They are deliberately marked **provisional** and **not submission-ready** until an estimator confirms actual equipment quantities and operating hours.

## Dry run

```bash
python -m app.tools.fuel_estimate_staging_import --operator "Staging Operator"
```

The dry run reports create/update/archive decisions and performs no database mutation.

## Controlled staging apply

A staging mutation requires explicit owner approval. Apply is rejected outside staging and requires acknowledgement that the estimates remain provisional:

```bash
ENVIRONMENT=staging python -m app.tools.fuel_estimate_staging_import \
  --operator "Staging Operator" \
  --apply \
  --confirm-provisional-estimates
```

If a tender closing date has passed, the command also requires `--confirm-expired-intake`. The importer then records the package as a historical opportunity with an unverified submission outcome rather than presenting it as active.

The apply is atomic and idempotent. It:

- reuses an existing Drive-import project/document when there is one unambiguous match;
- registers the baseline estimate link as archived and superseded without changing Drive;
- registers one provisional replacement estimate per tender;
- updates one draft bid workspace and current tender/project value;
- preserves submitted bids and refuses ambiguous project, tender, bid, or Drive-file matches.

## Verification after an approved apply

Record the project, tender, bid, baseline-document, and replacement-document IDs; run the importer a second time to prove idempotency; open both replacement links through the staging UI; and confirm that no duplicate active estimate is visible. Do not modify production.
