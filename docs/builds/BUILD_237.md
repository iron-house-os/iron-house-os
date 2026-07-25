# Build 237 — Deterministic Hands-Free Navigation

## Objective

Extend the management-only “Hey Chat” layer with safe, deterministic navigation
between Iron House OS modules while preserving the approved production appearance and
the assistant’s read-only operating boundary.

## Delivered

- Explicit voice directions such as “Hey Chat, open Financial Control” navigate
  directly to the requested module.
- Common Iron House names and practical aliases are mapped to existing authenticated
  routes, including projects, safety, estimating, documents, suppliers, RFQs,
  takeoff, equipment, reporting and management portals.
- Navigation is handled locally and does not send the direction to the AI service.
- The assistant speaks a short destination confirmation, then automatically resumes
  listening.
- Ordinary questions continue through the existing audited Iron House Chat API.

## Controls

- A navigation verb is required, reducing accidental routing from normal site
  conversation.
- Only fixed, existing application routes can be opened; spoken text cannot create an
  arbitrary URL.
- Navigation does not create, edit, approve, submit, send or delete company records.
- Access remains limited to administrators and operations managers.
- Browser microphone permission, visible listening state and the stop control remain
  unchanged.
- No protected visual-design file is changed.

## Approval gate

Build 237 may be merged only after the full CI and Release Readiness workflows pass.
Production deployment and authenticated acceptance remain separately controlled.
