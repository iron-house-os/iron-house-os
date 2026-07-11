# Build 182 — Tender-to-Project Conversion

Status: complete

The tender intake boundary creates and links a project workspace and RFQ package in the same transaction. Project identifiers, tender linkage, documents, estimating, RFQs, and correspondence must remain project-scoped.

## Acceptance criteria
- One tender produces one linked project workspace.
- Project and tender identifiers are mutually traceable.
- Repeated detail reads do not create duplicate projects.
- Downstream routes use the linked project identifier.
