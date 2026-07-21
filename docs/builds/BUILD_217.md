# Build 217: Full navigation and workflow audit

Build 217 removes the remaining dead-end navigation screens and adds a release gate that opens every visible Iron House OS tab on desktop and mobile layouts.

## Repairs

- Replaced the Equipment, Reporting, and Settings placeholders with working pages.
- Added equipment register create, list, filter, rate, and status-update APIs.
- Preserved the active project across project-aware navigation and project workflow links.
- Replaced raw project-ID entry on Project Operations and Document Operations with an automatic active-project selector.
- Automatically loads readiness, saved takeoffs, saved estimates, and project documents when the active project changes.
- Corrected Project Workspace links for Drawing Intelligence, Municipality Intelligence, Schedule, and Bid Package.
- Scoped the Document Library to the active project and prefilled new document records with that project.
- Made the long sidebar scrollable and repaired phone-width Project Workspace overflow.
- Added live Reporting and account/permission/password Settings screens.
- Redirected unknown authenticated routes safely to the Dashboard.

## Release gates

- Backend Ruff: passed.
- Backend Pytest: 109 passed.
- Frontend TypeScript: passed.
- Frontend Vitest: 20 passed.
- Frontend production build: passed.
- Playwright desktop/mobile route audit: all 17 visible tabs passed with no placeholder content, page exceptions, server-error state, or page-level horizontal overflow.
- Every tab passed automated serious/critical accessibility checks, including named form controls and keyboard-accessible scrolling regions.
