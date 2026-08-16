# Build 227 — Iron House Chat foundation

> Historical record: browser voice recognition from this build was retired by owner decision on 2026-08-16 after failed physical-device acceptance. The typed, read-only Iron House Chat foundation remains supported.

Build 227 adds a separate, management-only AI help surface inside Iron House OS.

## Delivered

- Dedicated `/iron-house-chat` page and navigation item visible only to administrators and operations managers.
- Server-side OpenAI Responses API boundary; the permanent credential is never returned to the browser.
- Account-isolated conversation and message history.
- Read-only system contract with sensitive-data and professional-approval guardrails.
- Audit event for every assistant request.
- Clear disabled state until a separate `OPENAI_API_KEY` is configured.

## Production activation

Set `OPENAI_API_KEY` in the backend production environment and optionally set
`OPENAI_CHAT_MODEL` (default: `gpt-5.6-sol`). Restart the backend after updating the
environment. Never place the credential in `VITE_*` variables or frontend files.

The assistant accepts typed questions and does not have write tools in this build.
