# RFQ Package Builder (Build 204)

Build 204 turns the existing RFQ package shell into a reviewable, supplier-specific package workflow.

## Workflow

1. Create an RFQ package with project, overall scope, return deadline, and supplier categories.
2. Add supplier recipients and optionally enter one scope item per line.
3. Generate missing supplier scopes from civil category defaults.
4. Complete the drawing and document checklist with attachment references.
5. Build individualized draft subjects, message bodies, scope lists, and attachment lists.
6. Manually record each recipient as `pending`, `sent`, `replied`, or `bounced`.

Building a package or changing a tracking status does **not** send an email or contact a supplier.

## Readiness contract

A package is ready only when:

- the overall package scope exists;
- at least one supplier recipient exists;
- every recipient has supplier-specific scope items; and
- every required document is marked attached with a storage reference.

Optional documents may remain pending or be marked not applicable.

## API

- `PUT /api/v1/rfqs/{id}/suppliers` saves recipients and generates missing scopes.
- `POST /api/v1/rfqs/{id}/supplier-scopes` generates missing scopes or force-regenerates them.
- `PATCH /api/v1/rfqs/{id}/suppliers/{recipient_id}/status` records manual delivery status and notes.
- `PUT /api/v1/rfqs/{id}/documents` saves the attachment checklist.
- `PATCH /api/v1/rfqs/{id}/documents/{document_id}/status` updates one checklist item.
- `GET /api/v1/rfqs/{id}/readiness` returns the four-part readiness score.
- `POST /api/v1/rfqs/{id}/build` returns supplier-specific draft packages and blockers.

## Known limitations

- Supplier scopes and tracking notes are stored in the RFQ package metadata until dedicated database fields are introduced.
- Attachment references are recorded but files are not uploaded by this build.
- Email delivery and Gmail/Drive persistence remain part of the next workflow-design task.
