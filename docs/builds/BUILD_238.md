# Build 238 — Hands-Free Session Controls

## Objective

Complete the management-only hands-free operating layer with deterministic local
session controls while preserving the approved production appearance and the
assistant's read-only boundary.

## Delivered

- "Hey Chat, go back" returns to the previous OS route.
- "Hey Chat, go home" opens the authenticated dashboard.
- "Hey Chat, repeat that" repeats the most recent spoken response without another API request.
- "Hey Chat, what can I say?" explains the available read-only voice capabilities.
- "Hey Chat, stop listening" turns off the microphone without requiring the screen control.
- Approved controls are resolved locally before navigation or Iron House Chat requests.

## Controls

- Voice controls cannot create, edit, approve, submit, send or delete company records.
- Only explicit, fixed phrases resolve as session controls.
- Unrecognized commands continue through the existing audited, read-only Iron House Chat API.
- Access remains limited to administrators and operations managers.
- Browser microphone permission, visible listening state and the manual stop control remain available.
- No protected visual-design file is changed.

## Verification

- Pure resolver tests cover every approved control and reject an unsafe mutation phrase.
- Provider tests prove repeat does not create a second API request.
- Provider tests prove voice stop disables microphone listening locally.
- Full CI and Release Readiness remain required before merge.

## Approval gate

Build 238 may be merged only after the full CI and Release Readiness workflows pass.
Production deployment and authenticated acceptance remain separately controlled.
