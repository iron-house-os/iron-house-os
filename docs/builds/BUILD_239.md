# Build 239 — Controlled Meeting Minutes

Build 239 adds a management-only meeting recorder and approved-minutes workflow to Iron House OS.

## Delivered

- Browser microphone recording with an unmistakable active-recording state and elapsed timer.
- Explicit confirmation that everyone present knows the meeting is being recorded before the
  microphone can start.
- Server-side transcription using a dedicated, configurable transcription model.
- An Iron House draft organized into summary, priority points, decisions, and assigned action items.
- Manual transcript entry when microphone recording is unavailable.
- Management review and approval before a meeting record can be saved.
- Optional project linkage, meeting date, attendees, owner, and audit metadata.
- Management-only API and page access for administrators and operations managers.

## Privacy and governance controls

- Raw audio is used for transcription and is not added to document storage or the database.
- List responses exclude transcripts; full records require an authenticated management detail request.
- Provider credentials remain server-side and are never returned to the browser.
- Audio uploads are restricted to supported formats and the provider's 25 MB limit.
- AI output is explicitly labelled as a draft until management reviews and saves it.
- Audit events record the action, models, size, record ID, and retention policy without copying audio
  or transcript content into audit metadata.
- The workflow warns users not to discuss passwords, API keys, SINs, banking, medical, or payroll
  information.

## Release controls

- `MEETING_MINUTES_ENABLED` is an independent production kill switch.
- `OPENAI_TRANSCRIPTION_MODEL` defaults to `gpt-4o-mini-transcribe`.
- Alembic revision `20260725_0010` creates the controlled meeting record.
- The authenticated release smoke checks the management status, list endpoint, and no-audio-retention
  policy.
- Production deployment remains a separate approval and verification step.
