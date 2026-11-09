# Build 175 — Frontend Role Enforcement

## Principle
The backend remains the security authority. Frontend controls improve usability but never replace API authorization.

## Required behavior
- Load the authenticated principal and permission set before rendering protected modules.
- Hide navigation items the principal cannot access.
- Disable unauthorized actions with a clear explanation when visibility is operationally useful.
- Redirect unauthenticated users to login.
- Show a dedicated forbidden state for authenticated users lacking permission.
- Clear cached principal and tenant data on logout or session expiry.

## Permission mapping
Each route and mutating control must declare a required permission. Initial examples:
- `projects.read`, `projects.write`
- `documents.read`, `documents.write`, `documents.audit`
- `suppliers.read`, `suppliers.write`
- `rfqs.read`, `rfqs.write`, `rfqs.send`
- `estimates.read`, `estimates.write`, `estimates.approve`
- `users.manage`, `settings.manage`

## Tests
Frontend tests must cover protected-route redirects, module visibility, forbidden states and logout cache clearing.
