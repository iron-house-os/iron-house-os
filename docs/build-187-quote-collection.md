# Build 187 — Quote Collection

Status: complete

## Quote record contract
- Supplier, project, RFQ package, revision, received date, currency, subtotal, taxes, total, and source document.
- Scope inclusions, exclusions, alternates, validity period, lead time, and contact details.
- Original quote files remain immutable; normalized values are stored separately.

Multiple revisions from the same supplier are retained and the current revision is explicitly identified.
