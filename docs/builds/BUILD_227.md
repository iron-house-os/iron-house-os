# Build 227 — Iron House Chat foundation

Build 227 adds a separate, management-only AI help surface inside Iron House OS.

## Delivered

- Dedicated `/iron-house-chat` page and navigation item visible only to administrators and operations managers.
- Server-side OpenAI Responses API boundary; the permanent credential is never returned to the browser.
- Account-isolated conversation and message history.
- Read-only system contract with sensitive-data and professional-approval guardrails.
- Audit event for every assistant request.
- Opt-in browser voice recognition using the phrase “Hey Chat” and spoken answers.
- Clear disabled state until a separate `OPENAI_API_KEY` is configured.

## Production activation

Set `OPENAI_API_KEY` in the backend production environment and optionally set
`OPENAI_CHAT_MODEL` (default: `gpt-5.6-sol`). Restart the backend after updating the
environment. Never place the credential in `VITE_*` variables or frontend files.

Voice requires browser microphone permission and operates only while the OS page is
open. The assistant does not have write tools in this build.

