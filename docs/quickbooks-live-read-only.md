# QuickBooks Online live read-only preparation

Issue: #401. This slice prepares IHOS for a separately approved live-company
OAuth connection. It does not enable or deploy the live connection and it does
not add any accounting write.

## Exact boundary

The only QuickBooks Accounting API operation implemented by this integration is
`GET CompanyInfo`. IHOS uses it to verify the company name and realm selected in
the Intuit consent flow. There are no IHOS routes or controls for creating,
updating, emailing, paying, voiding, or deleting QuickBooks records.

Intuit's `com.intuit.quickbooks.accounting` OAuth scope is broader than this
IHOS implementation. The UI must therefore say **IHOS read-only** rather than
claiming that Intuit issued a read-only token.

## Intuit prerequisite

Live QuickBooks data requires Intuit production credentials. Intuit requires
the app details and app-assessment process even for a private/internal app. Use
the production Client ID and Client Secret only after Intuit has approved and
issued them:

- OAuth setup: <https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0>
- OAuth key guidance: <https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/faq>

The approved production redirect URI is:

```text
https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback
```

Never place the Client Secret, authorization code, access token, refresh token,
or callback query string in GitHub, chat, screenshots, logs, or browser storage.

## Fail-closed settings

| Setting | Staging | Live activation |
| --- | --- | --- |
| `QUICKBOOKS_ENABLED` | `false` or database-managed sandbox setup | Keep `false` when credentials will be entered through the administrator UI |
| `QUICKBOOKS_FORCE_DISABLED` | `false` during an approved test | `true` is the emergency kill switch |
| `QUICKBOOKS_ENVIRONMENT` | `sandbox` | `production` |
| `QUICKBOOKS_LIVE_READ_ONLY_APPROVED` | `false` | `true` only after owner approval |
| redirect / return URLs | staging host | production host |

Production mode cannot save credentials, start OAuth, or call CompanyInfo while
`QUICKBOOKS_LIVE_READ_ONLY_APPROVED=false`. Disconnect and credential removal
remain available so recovery does not depend on the enable gate.

Live QuickBooks is also bound to the protected IHOS production application
environment. Shared staging hardcodes `QUICKBOOKS_ENVIRONMENT=sandbox` and
`QUICKBOOKS_LIVE_READ_ONLY_APPROVED=false`; environment-file overrides cannot
select the Intuit production host there.

## Controlled release sequence

1. Merge #401 only after CI, security review, and sandbox regression evidence.
2. Keep shared staging on `sandbox`; reverify the existing sandbox connection.
3. Complete the Intuit app details and assessment without exposing production
   credentials.
4. Obtain production keys and confirm the production redirect URI in Intuit.
5. Open a separate activation issue/PR that changes the production target to
   `production`, records the owner's live-read-only approval, and provisions a
   protected random `QUICKBOOKS_TOKEN_ENCRYPTION_KEY` of at least 32 characters
   through the approved production secret path. Never place that key in GitHub,
   chat, screenshots, or deployment logs.
6. Pass CI and release readiness, then request the protected production
   deployment approval. Do not bypass the required reviewer.
7. An IHOS administrator enters the production keys in Financial Control. The
   browser clears the Client Secret after submission.
8. Authorize the exact Iron House QuickBooks Online company and verify the
   returned company name and realm. Do not proceed if the company is wrong.
9. Confirm there are still no invoice, customer, bill, payment, payroll, tax,
   journal-entry, attachment, email, or sync actions.

## Rollback

1. Set `QUICKBOOKS_FORCE_DISABLED=true` for the emergency application kill
   switch.
2. Use the administrator disconnect control to attempt Intuit revocation and
   clear local encrypted tokens.
3. Remove the saved production credentials from IHOS after disconnection.
4. Revoke the app connection in Intuit if IHOS reports that revocation could not
   be confirmed.
5. Roll back the application release through the protected production workflow.

Rollback does not change any QuickBooks accounting record because this slice
contains no accounting mutation operation.
