# Build 174 — Organization and User Tenancy Model

## Primary tenant
`Iron House Civil Constructors` is the initial organization. Every operational record must be associated with an organization ID.

## User lifecycle
- Invited
- Active
- Suspended
- Disabled

## Initial roles
- `owner`: full company and security administration
- `administrator`: user, configuration and workflow administration
- `estimator`: tenders, suppliers, RFQs, quotes, estimates and bid packages
- `project_manager`: projects, documents, field records and reporting
- `field_user`: assigned projects, field documents and permitted updates
- `viewer`: read-only access to authorized modules

## Isolation requirements
- All tenant-owned database queries must be organization-scoped.
- Cross-organization identifiers must return `404` or an equivalent non-disclosing response.
- Organization context must come from the authenticated principal, not a trusted client parameter.
- Audit records must preserve organization, principal, role and action.

## Acceptance criteria
Automated tests must prove that users cannot read, update, export or delete records belonging to another organization.
