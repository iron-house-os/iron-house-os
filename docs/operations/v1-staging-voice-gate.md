# Version 1.0 staging voice gate

## Control record

- Parent issue: #85
- Work item: #86
- Branch: `sprint1/voice-stability-gate`
- Production baseline: Build 237 at `55afaa689603263c1ad415436e90cce6679808c3`
- Status: In progress
- Approval gate: human approval before merge; physical iPad Safari acceptance before release enablement

## Containment

Hands-free Hey Chat is controlled at frontend build time by:

```text
VITE_HEY_CHAT_VOICE_ENABLED
```

The flag fails closed. Only `true`, `1`, `on`, or `yes` enable the voice control. The frontend Docker image defaults it to `false`.

For an isolated staging image only:

```text
--build-arg VITE_HEY_CHAT_VOICE_ENABLED=true
```

Do not add this setting to `/etc/iron-house-os/production.env`, change the production Compose configuration, or deploy this branch to the production droplet.

## Automated acceptance

The staging branch must pass:

- TypeScript validation.
- Full Vitest suite.
- Production frontend build.
- Visual-design lock.
- Backend Ruff and pytest gates.
- Ten sequential mocked iPad navigation commands from one enable action.
- Recognition handler and restart-timer cleanup after command cycling and unmount.
- Pending voice request abort with no late spoken response after Stop.

## Remaining acceptance

Automated Web Speech mocks do not prove Apple's live recognition service. Before the flag can be considered for a release candidate, record a physical iPad test with:

- device model;
- iPadOS and Safari versions;
- Siri enabled;
- tester and date;
- ten consecutive commands without re-enabling;
- Stop, permission denial, background/return, and network-interruption results;
- confirmation that no duplicate command or recognition session occurred.

