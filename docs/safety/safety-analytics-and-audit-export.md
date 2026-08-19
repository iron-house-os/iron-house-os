# Safety analytics and audit export

Issue #70 Phase 4 adds management-only operational analytics and a privacy-safe CSV export for safety controls.

## Access and purpose

- Only `admin` and `operations_manager` accounts can read the analytics endpoint or download the export.
- Indicators support workflow follow-up. They do not decide or certify legal or regulatory compliance.
- The server calculates the indicators across the durable register rather than the 200-record field bootstrap window.

## Privacy boundary

The CSV includes control metadata for FLHAs, toolbox talks, equipment inspections, permits, corrective actions and emergency action cards. It omits narrative details, employee identifiers, worker names and submitter identities.

Incident and first-aid occurrence rows are excluded completely. Management analytics include only an aggregate count of incidents that remain open; they do not include incident details. First-aid occurrences are excluded from analytics and export data.

## Spreadsheet safety

Text cells that begin with a spreadsheet formula prefix are neutralized before export. The resulting CSV is an operational audit aid and must still receive human review before it is used for an external report or policy conclusion.
