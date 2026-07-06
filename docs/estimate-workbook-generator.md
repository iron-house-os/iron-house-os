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
- Quote Comparison

## Notes

The generator lives in `backend/app/services/estimate_workbooks.py`.

It uses the estimate engine to calculate the summary, then writes a formatted workbook for estimator review.

Required backend dependency:

`openpyxl==3.1.5`

If the dependency is not already installed, add it to `backend/requirements.txt`.
