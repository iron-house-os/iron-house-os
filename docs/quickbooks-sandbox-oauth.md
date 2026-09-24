# QuickBooks Online sandbox OAuth

Issue: #391

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

## Server configuration

Set these values only in the protected server environment:

```text
QUICKBOOKS_ENABLED=true
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_CLIENT_ID=<Intuit development client ID>
QUICKBOOKS_CLIENT_SECRET=<Intuit development client secret>
QUICKBOOKS_REDIRECT_URI=https://<approved-host>/api/v1/finance/quickbooks/oauth/callback
QUICKBOOKS_FRONTEND_RETURN_URL=https://<approved-host>/finance
QUICKBOOKS_TOKEN_ENCRYPTION_KEY=<independent random value of at least 32 characters>
```

Never place the client secret, encryption key, authorization code, access token, or refresh token in GitHub, screenshots, chat, URLs, browser storage, logs, or audit metadata.

## Controlled flow

1. An IHOS administrator opens Financial Control and selects **Connect sandbox**.
2. IHOS stores only a SHA-256 digest of a one-time state value that expires after ten minutes.
3. The administrator signs into Intuit and selects the sandbox company.
4. Intuit returns the browser to the exact IHOS callback with the code, state, and `realmId`.
5. IHOS validates and consumes the state once, exchanges the code server-side, encrypts both tokens, and calls read-only `CompanyInfo`.
6. IHOS stores the sandbox realm and verified company name. A different realm is refused until the current connection is explicitly disconnected.
7. Disconnect requires a separate confirmation, attempts Intuit token revocation, and clears the local encrypted tokens even if Intuit is temporarily unavailable.

## Verification

- Backend tests: `PYTHONPATH=backend pytest -q tests/backend/test_quickbooks.py`
- Frontend tests: `npm test -- --run src/components/QuickBooksConnectionCard.test.tsx`
- Backend lint: `ruff check backend/app tests/backend/test_quickbooks.py`
- Frontend type check: `npm run lint`

Staging evidence must show the registered staging redirect, successful sandbox company verification, single-use state rejection, no tokens in responses/logs, and a confirmed disconnect before any production deployment request.

## Rollback

Disable `QUICKBOOKS_ENABLED`, disconnect the sandbox company from IHOS, revoke the Intuit app connection if needed, and roll back the application release. The migration downgrade removes only the sandbox OAuth connection/state tables; it does not touch IHOS invoices or any QuickBooks accounting record.
