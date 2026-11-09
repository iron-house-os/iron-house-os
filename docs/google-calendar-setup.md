# Google Calendar production setup

This guide configures the controlled Google Calendar integration for Iron House OS production.

## Google Cloud configuration

1. Use an Iron House-controlled Google Cloud project.
2. Enable the Google Calendar API.
3. Configure the OAuth consent screen as **Internal** when the participating accounts are in the
   Iron House Google Workspace organization.
4. Create an OAuth 2.0 client with application type **Web application**.
5. Add this exact authorized redirect URI:

   `https://os.ironhousecivil.com/api/v1/google-calendar/oauth/callback`

6. If Google Workspace blocks the requested scope, have the Workspace administrator review and
   approve the application.

The application requests only:

`https://www.googleapis.com/auth/calendar.events.owned`

Do not add broader Calendar scopes unless a later approved build requires them.

## Production environment

Set these values in `/etc/iron-house-os/production.env`:

```dotenv
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_CLIENT_ID=<google-oauth-client-id>
GOOGLE_CALENDAR_CLIENT_SECRET=<google-oauth-client-secret>
GOOGLE_CALENDAR_REDIRECT_URI=https://os.ironhousecivil.com/api/v1/google-calendar/oauth/callback
GOOGLE_CALENDAR_FRONTEND_RETURN_URL=https://os.ironhousecivil.com/google-calendar
GOOGLE_CALENDAR_TOKEN_ENCRYPTION_KEY=<dedicated-random-secret>
```

Use a dedicated high-entropy value for `GOOGLE_CALENDAR_TOKEN_ENCRYPTION_KEY`. Do not commit real
credentials or encryption keys to the repository.

## Controlled activation

1. Keep `GOOGLE_CALENDAR_ENABLED=false` until the production migration, readiness checks, and
   authenticated smoke test pass.
2. Confirm the production callback exactly matches the Google Cloud OAuth client.
3. Enable the integration and restart the backend through the approved deployment workflow.
4. As an administrator or operations manager, open **Google Calendar**, connect an authorised Iron
   House account, and verify upcoming owned events.
5. Create a non-inviting test event only after reviewing and confirming the details.
6. Verify the event appears in both Iron House OS and the account's primary Google Calendar.

Disconnecting revokes the provider token before clearing the encrypted local credentials. If Google
cannot confirm revocation, the local credentials remain in place and the operation reports a failure
for controlled follow-up.
