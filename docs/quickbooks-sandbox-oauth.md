# QuickBooks Online sandbox OAuth

Issue: #391

Security hardening follow-up: #393

Parent objective: #389
Status: sandbox-only connection foundation

## Boundary

This integration connects one QuickBooks Online **sandbox** company to IHOS Finance. It verifies the company identity through the read-only `CompanyInfo` endpoint. It does not create, update, export, email, pay, void, or delete any QuickBooks accounting record.

Production QuickBooks credentials, live-company authorization, and every accounting write remain behind the separate owner and accountant approval gate in #389.

## Registered redirect URI

For the IHOS production host, register this exact URI in the Intuit app's **Development** redirect URI list:

```text
https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback
```

Keep the existing Intuit playground and quickstart redirect URIs. Add the IHOS URI as a third entry. The URI registration alone does not enable the integration or expose a credential.

For staging, use the approved HTTPS staging hostname with the same path. Do not use `staging.invalid`; it is an example placeholder.

## Secure administrator configuration

An IHOS administrator can enter the Intuit **Development** Client ID and Client Secret in Financial Control. The HTTPS request body is never logged, the browser clears both fields after submission, and the API never returns either stored value. The Client Secret and an independently generated token-encryption key are encrypted at rest using a key derived from the protected IHOS application secret.

Credential replacement or removal is blocked while a sandbox company is connected. Disconnect first so IHOS can attempt provider revocation and clear the encrypted OAuth tokens.

The protected server environment remains a supported fallback for recovery or managed deployments:

Set these values only in the protected server environment:

```text
QUICKBOOKS_ENABLED=true
QUICKBOOKS_FORCE_DISABLED=false
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_CLIENT_ID=<Intuit development client ID>
QUICKBOOKS_CLIENT_SECRET=<Intuit development client secret>
QUICKBOOKS_REDIRECT_URI=https://<approved-host>/api/v1/finance/quickbooks/oauth/callback
QUICKBOOKS_FRONTEND_RETURN_URL=https://<approved-host>/finance
QUICKBOOKS_TOKEN_ENCRYPTION_KEY=<independent random value of at least 32 characters>
```

Never place the client secret, encryption key, access token, or refresh token in GitHub, screenshots, chat, URLs, browser storage, logs, or audit metadata. Enter a Client Secret only in the password field on the authenticated IHOS Financial Control page over HTTPS. Intuit temporarily returns the authorization code and state in the callback URL; never copy or retain that callback URL, and never include it in screenshots, logs, or support messages.

The deployed frontend proxy, host proxy, and backend runtime suppress access logging for the OAuth callback path. Callback-specific proxy error logging is also discarded so an upstream outage cannot persist the request URI. Every callback outcome uses a sanitized redirect that disables caching and referrer forwarding, including query-validation failures, expired or unauthorized sessions, and unexpected server errors, so the short-lived authorization code is not retained or propagated after the redirect.

## Controlled flow

1. An IHOS administrator opens Financial Control and selects **Connect sandbox**.
2. IHOS stores only a SHA-256 digest of a one-time state value that expires after ten minutes.
3. The administrator signs into Intuit and selects the sandbox company.
4. Intuit returns the browser to the exact IHOS callback with the code, state, and `realmId`.
5. IHOS atomically validates and consumes the state once, exchanges the code server-side, encrypts both tokens, and calls read-only `CompanyInfo`.
6. IHOS stores the sandbox realm and verified company name. A different realm is refused until the current connection is explicitly disconnected.
7. Disconnect requires a separate confirmation, attempts Intuit token revocation, and clears the local encrypted tokens even if Intuit is temporarily unavailable.

## Verification

- Backend tests: `PYTHONPATH=backend pytest -q tests/backend/test_quickbooks.py`
- Frontend tests: `npm test -- --run src/components/QuickBooksConnectionCard.test.tsx`
- Backend lint: `ruff check backend/app tests/backend/test_quickbooks.py`
- Frontend type check: `npm run lint`

Staging evidence must show the registered staging redirect, successful sandbox company verification, single-use state rejection, no tokens in responses/logs, and a confirmed disconnect before any production deployment request.

## Rollback

Set `QUICKBOOKS_FORCE_DISABLED=true` to block OAuth even when encrypted credentials have been saved in IHOS. Then use the administrator disconnect control to attempt Intuit revocation and clear the local encrypted tokens. The disconnect recovery path remains available while the feature is disabled and clears local tokens even if decryption or provider revocation fails. Remove the saved database credentials in Financial Control when rollback requires a full local credential purge. Revoke the Intuit app connection directly if the IHOS status reports that revocation was not confirmed, then roll back the application release. The migration downgrade removes only the sandbox OAuth connection/state tables; it does not touch IHOS invoices or any QuickBooks accounting record.
