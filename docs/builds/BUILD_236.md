# Build 236 — Hands-Free Hey Chat

## Task card

- **Lead function:** System Governance
- **Supporting functions:** Quality Assurance, Administration and Communications
- **Owner:** Jeremie Peters
- **Priority:** High
- **Status:** Ready
- **Environment:** Development only
- **Approval gate:** Pull-request review and green release gates before merge or deployment

## Objective

Extend the management-only Iron House Chat foundation into a hands-free voice layer
that remains available across Iron House OS pages without weakening its read-only,
account-isolated or privacy controls.

## Delivered

- One explicit microphone-permission action enables Hey Chat across the open,
  authenticated Iron House OS tab.
- “Hey Chat” accepts a command in the same sentence or speaks a short acknowledgement
  and accepts the next spoken sentence.
- Recognition pauses while the assistant is working or speaking, then automatically
  resumes to avoid hearing its own answer.
- Interrupted browser recognition automatically restarts while the user keeps the
  control enabled.
- A persistent, visible microphone state and stop control provide clear privacy
  indication from every OS page.
- Access remains limited to administrators and operations managers.
- Voice requests continue through the existing audited, read-only Iron House Chat API.

## Boundaries and controls

- Browser security requires the initial enable action and microphone permission.
- Listening operates only while the authenticated Iron House OS tab remains open; it
  is not a device-level or lock-screen assistant.
- No new write tools, operational approvals or external actions are introduced.
- Passwords, SINs, banking, medical and payroll information remain prohibited inputs.

## Verification

- 157 backend tests passed.
- 26 frontend tests passed, including five focused voice-assistant tests.
- Four Playwright desktop, mobile and accessibility release-gate tests passed.
- Ruff, TypeScript and the production frontend build passed.
- The visual-design lock passed with no protected-file changes.

## Record

The pull request and release-gate results will be the Build 236 system of record.
Production deployment remains separately controlled and must not be inferred from
merge or CI completion.
