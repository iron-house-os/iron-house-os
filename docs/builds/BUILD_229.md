# Build 229 — Project Brain migration

Build 229 turns Iron House Chat into a durable project-memory workspace.

## Delivered

- Source-ranked Project Brain records with management decisions above historical chat discussions.
- Canonical Iron House operating context for identity, visual lock, civil execution model, suppliers, portals, cost codes, materials, loads, and agent approval policy.
- Secure import of ChatGPT data-export ZIP or JSON files up to 75 MB.
- Automatic selection of Iron House OS conversations and rejection of unrelated chats.
- Redaction of common API-key, token, secret, and password patterns during import.
- Idempotent imports: existing conversation records are refreshed rather than duplicated.
- Keyword-ranked memory retrieval injected into each AI request.
- Audit record of imports and memory source IDs used for assistant answers.
- Management UI showing Project Brain source count and import results.

## Authority order

1. Deployed production state.
2. Merged builds and approved documentation.
3. Explicit management decisions.
4. Newer project conversations.
5. Older discussions and abandoned proposals.

The separate server-side OpenAI credential remains required for generated answers. Import and storage work without it.
