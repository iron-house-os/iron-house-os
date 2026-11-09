# Estimate Workbook Generator

## Endpoint

`POST /api/v1/estimates/workbook`

Accepts the same estimate payload as `POST /api/v1/estimates/summary` and returns an Excel workbook download.

## Workbook Sheets

- Summary
- Line Items
- Production Rates
- Markups
- Risks
- Assumptions
- Exclusions
- Quote Comparison

## Notes

The generator lives in `backend/app/services/estimate_workbooks.py`.

It uses the estimate engine to calculate the summary, then writes a formatted workbook for estimator review. Assumptions and exclusions are kept on separate sheets so each can be reviewed and issued independently.

The line-item total remains an estimator-readable Excel formula. Empty estimates use an explicit `=0` total instead of a reversed cell range.

Required backend dependency:

`openpyxl==3.1.5`

The dependency is pinned in `backend/requirements.txt`.

Regression coverage lives in `tests/backend/test_estimate_workbooks.py` and verifies the sheet contract, formula output, quote selection display, empty-state wording, and safe filenames.
