# Build 70 Cutover Note

Build 70 marks the point where IHOS has enough connected MVP workflow to begin local operator testing.

## Cutover condition

Before using IHOS on a real bid, confirm:

- Backend starts.
- Frontend starts.
- `/readiness` returns ready.
- Project creation works.
- Quantity takeoff summary works.
- Saved takeoff appears in Project Operations.
- Estimate workspace can be saved and reloaded.
- RFQ linkage generates package drafts.

## Operating rule

IHOS is not yet an autonomous estimator. It is a structured bid assistant. All quantities, rates, quotes, exclusions, assumptions, and final bid prices require estimator review.
