# Audit Log Plan

## Events to capture

- Project created, updated, archived.
- Document uploaded, superseded, archived.
- Takeoff saved.
- Estimate workspace saved.
- RFQ package created or updated.
- Supplier recipient added or removed.
- Quote entered or selected.
- Final workbook exported.
- Bid package generated.

## Event fields

- Event ID.
- Timestamp.
- User ID.
- Project ID.
- Entity type.
- Entity ID.
- Action.
- Before/after metadata where appropriate.

## MVP approach

Start with append-only database records. Add UI timeline later.
