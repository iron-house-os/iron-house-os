# Private IHOS chat management connector

Issue #412; tender source inventory #411. This is an isolated OAuth resource server, not an activated connection.

## What is implemented

Run `python -m app.chat_connector` from backend only after installing `requirements-connector.txt`.
The service binds loopback port 8091 by default. It does not change the existing FastAPI application,
browser login, database schema, production Compose configuration, domain or proxy.

Tools: connection_status, bounded list_projects (includes Trash), preview_tender_intake and
apply_tender_intake. Initial scope is administrator-only. A current active administrator without
a password-reset requirement is resolved on every call; OAuth client identity is never the user identity.

Every bearer grant is introspected over a fixed HTTPS endpoint using protected resource-server credentials.
The verifier requires active=true, exact configured issuer, matching MCP resource audience, an expiry within
one hour, approved OAuth client ID, read scope and a preconfigured issuer-subject to IHOS account UUID mapping.
Introspection redirects and failures fail closed; no token cache. Read-only is default; writes additionally
require both the write kill switch and ihos:projects:write. The MCP SDK provides transport and resource discovery.

Source intake permits only a narrow field allowlist. Unknown fields cannot inject award, financial,
supplier or safety state. New records are opportunities without job numbers. Same-name/tender matches
are conflicts until an exact existing_project_id is reviewed; linking adds source metadata only.
Trash is included in reconciliation and is never recreated. Changed source content is a conflict.
Signed previews bind actor/session version, exact input and observed matching project state for ten minutes.
Retries verify the existing source record. PostgreSQL table locking serializes source reconciliation with
ordinary project writes; deterministic project IDs enforce retry uniqueness.
Each tool handles one project: batch retries cannot silently replay an entire financial package.

## Configuration still required — activation blocker

No OAuth authorization server or resource introspection credentials have been discovered/configured for IHOS.
This module intentionally does NOT implement an ad hoc authorization server, issue demo tokens, copy browser
cookies into chat, or reuse the bootstrap administrator password. An OAuth 2.1 provider must be provisioned
and tested with ChatGPT authorization-code/PKCE, discovery, resource binding, client registration and revocation.

Required protected settings (do not put actual values in issues, chat or git):
- IHOS_MCP_ENABLED=true (default is false; absent mandatory settings prevent startup)
- IHOS_MCP_WRITES_ENABLED=false for initial connection verification
- IHOS_MCP_RESOURCE_URL: exact deployed HTTPS URL ending /mcp
- IHOS_MCP_ISSUER_URL: exact issuer emitted by introspection, including trailing slash if present
- IHOS_MCP_INTROSPECTION_URL: fixed HTTPS RFC 7662 endpoint; no redirects
- IHOS_MCP_INTROSPECTION_CLIENT_ID and IHOS_MCP_INTROSPECTION_CLIENT_SECRET
- IHOS_MCP_ALLOWED_CLIENT_IDS: JSON array of explicitly registered ChatGPT OAuth client IDs
- IHOS_MCP_SUBJECT_ACCOUNTS: JSON object mapping provider sub to verified IHOS user UUID
- IHOS_MCP_PORT: loopback port, default 8091

A public TLS reverse proxy must forward /mcp and /.well-known/oauth-protected-resource/mcp to this loopback
service without stripping Authorization. Preserve the public Host or the configured loopback host.
Do not expose the database or the loopback port. Proxy/service/provider configuration requires the normal
protected rollout. Existing production runtime does not install or start this optional service automatically.

## Verification before activation

1. Install connector dependencies into an isolated disposable environment; run Ruff and backend pytest.
2. Test PostgreSQL concurrent ordinary inserts vs intake, rollback, process restart and retries.
3. Deploy to staging only; test real OAuth login, wrong resource/client, revoked grant, account deactivation
   and read-only operation through actual HTTP. Unit mocks do not establish provider or staging readiness.
4. Connect the staging server as a private ChatGPT custom MCP plugin. Verify connection_status reports the
   expected IHOS account and staging release. Exercise source preview/create/link/readback using synthetic data.
5. Preserve owner review and protected production approval. Deploy service/provider/proxy settings only after
   staging evidence. Confirm exact public production identity and account before enabling project writes.
6. Connect the production plugin from ChatGPT web and complete account consent. This must be done by the owner.
7. Use #411's 29 project identities, verify current inventory, preview each source and create/link only exact
   approved results. Preserve document provenance through folder links; this slice does not upload file bytes
   or create quote/invoice records. Verify every IHOS ID and result before reporting jobs imported.

## Rollback and limits

Stop the connector or set its enabled/write switches false and revoke its OAuth grants. No schema migration,
production app update or automatic project deletion is required. Retain created opportunity/source audit history.
A provider or deployment is not bundled here; do not describe this PR as restored live management.
Broader updates, project deletion, accounting posting, safety approval, customer quote issuance, arbitrary
HTTP requests, shell and deployment are deliberately absent.

Official references:
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/api/docs/guides/custom-mcp-server
- https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0
