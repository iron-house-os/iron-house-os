# Build 219: Production-wide workflow compatibility repair

## Outcome

Build 219 replaces one-tab-at-a-time production repairs with a single compatibility gate for every navigation module. It normalizes enum-backed values inherited from the pre-Alembic database, prevents serializers from raising on legacy strings, and blocks readiness when persisted workflow values fall outside the supported contracts.

## Repaired data contracts

- Project status
- Document category and status
- RFQ package, recipient, and attachment status
- Tender status (retained from Build 218)
- Equipment status
- User account role

The migration preserves records, translates known legacy meanings, assigns conservative fallbacks to unknown values, and adds database constraints so incompatible values cannot be reintroduced.

## Release protection

- The authenticated release smoke reads Projects, Suppliers, RFQs, Tenders, Documents, Equipment, Users, Settings permissions, and Estimating rates.
- It traverses every stored project, RFQ package, tender, document, and supplier detail dependency used by the UI.
- Runtime readiness verifies all required tables, the exact Alembic revision, every persisted workflow value, and document storage.
- Production cutover performs only anonymous readiness over HTTP loopback and runs authenticated smoke over HTTPS, matching the secure-cookie policy.

## Verification

- Ruff clean
- 112 backend tests passed
- Build 208 SQLite adoption regression passed with populated legacy values
- PostgreSQL Build 208 adoption and the full authenticated release smoke are required by GitHub release readiness before deployment
