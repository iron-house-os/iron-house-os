# Database Review Plan

Before production use, review the database against the current SQLAlchemy models.

## Tables to confirm

- `projects`
- `documents`
- `drawings`
- `takeoffs`
- `bids`
- `rfqs`
- `rfq_packages`
- `rfq_package_documents`
- `rfq_package_supplier_recipients`
- `suppliers`
- `quotes`

## Checks

- Primary keys exist.
- Foreign keys match models.
- JSON fields are supported.
- Date/time fields use consistent timezone handling.
- Required fields are not nullable unexpectedly.
- Indexes exist for project-linked records.

## Migration goal

Add Alembic migrations or a controlled schema migration workflow before hosted deployment.
