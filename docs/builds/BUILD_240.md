# Build 240 — Controlled Google Calendar

Build 240 adds management-controlled Google Calendar access to Iron House OS.

## Delivered

- Management-only Google OAuth connection and disconnection.
- Upcoming-event visibility from the signed-in manager's primary Google Calendar.
- Explicitly confirmed creation of owned events on that primary calendar.
- Optional Iron House project linkage, location, and description.
- Google Calendar status in the application without exposing access or refresh tokens.

## Authority and governance controls

- Access is limited to administrators and operations managers.
- The integration requests only the `calendar.events.owned` OAuth scope.
- Event creation requires a deliberate confirmation after reviewing the event details.
- Build 240 cannot add attendees, send invitations, update events, or delete events.
- Google API requests use `sendUpdates=none`.
- OAuth state is user-bound, hashed in storage, single-use, and expires after 10 minutes.
- Access and refresh tokens are encrypted at rest and never returned to the browser.
- Audit metadata records event IDs, project IDs, times, and outcomes without copying event
  descriptions or OAuth tokens.

## Release controls

- `GOOGLE_CALENDAR_ENABLED` is an independent production kill switch.
- Google OAuth client credentials and the token-encryption key remain server-side.
- Alembic revision `20260726_0011` creates the connection and OAuth-state records.
- The authenticated release smoke checks the management status endpoint, least-privilege scope, and
  absence of protected token fields.
- Production OAuth requires the exact authorized redirect URI documented in
  `docs/google-calendar-setup.md`.
- Production deployment remains a separate approval and verification step.
