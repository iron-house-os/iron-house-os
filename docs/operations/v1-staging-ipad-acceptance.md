# Version 1.0 physical iPad Safari acceptance

## Control record

- Parent issue: #85
- Work item: #88
- Branch: `sprint1/regression-acceptance`
- Dependencies: PR #91 and PR #95
- Production baseline: Build 237 at `55afaa689603263c1ad415436e90cce6679808c3`
- Status: Pending physical-device execution
- Approval gate: human approval before merge; no production enablement

The automated WebKit project uses an iPad device profile and an injected Web
Speech lifecycle mock. It proves browser integration, navigation, cleanup, and
regression behavior, but it does not prove Apple's live speech-recognition
service. Complete this record on a physical iPad against the isolated staging
host before Sprint 1 can be accepted.

## Required device record

Do not mark this gate passed while any value is blank.

| Field | Recorded value |
| --- | --- |
| Release candidate commit |  |
| Isolated staging URL |  |
| iPad model |  |
| iPadOS version |  |
| Safari version |  |
| Siri enabled |  |
| Tester |  |
| Test date and local time |  |
| Network used |  |

## Preconditions

- Confirm the URL is the isolated Version 1.0 staging host, not production.
- Confirm the staging build explicitly enables `VITE_HEY_CHAT_VOICE_ENABLED`
  and `VITE_PERFORMANCE_OBSERVABILITY_ENABLED`.
- Confirm the account is a staging-only management account.
- Enable Siri and allow Safari microphone access.
- Open Safari developer tools or the remote Web Inspector so the final
  `window.__IHOS_PERFORMANCE__.snapshot()` can be copied into this record.
- Start from a fresh Safari tab and sign in once.

## Ten-command sequence

Click **Enable Hey Chat** once. Do not click it again during this sequence.

| # | Spoken command | Expected result | Pass/fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | Hey Chat, go home | Dashboard opens |  |  |
| 2 | Hey Chat, open financial control | Financial Control opens |  |  |
| 3 | Hey Chat, go back | Previous page opens |  |  |
| 4 | Hey Chat, open safety program | Safety Program opens |  |  |
| 5 | Hey Chat, go home | Dashboard opens |  |  |
| 6 | Hey Chat, open equipment | Equipment opens |  |  |
| 7 | Hey Chat, go back | Previous page opens |  |  |
| 8 | Hey Chat, open supplier database | Supplier Database opens |  |  |
| 9 | Hey Chat, open project operations | Project Operations opens |  |  |
| 10 | Hey Chat, go home | Dashboard opens |  |  |

Pass requires all ten commands to complete after the single enable action,
with no duplicate navigation, answer, or recognition session.

## Lifecycle and fault checks

Run each check from a freshly enabled voice session.

| Check | Expected result | Pass/fail | Notes |
| --- | --- | --- | --- |
| Stop button | Listening, speech, timers, and pending request stop immediately |  |  |
| Microphone permission denied | Voice fails closed and requires explicit re-enable |  |  |
| Quiet/no-speech interval | One bounded retry occurs; no duplicate session |  |  |
| Repeated recognizer end | Retry is bounded and never creates overlapping sessions |  |  |
| Background Safari, then return | Voice remains off until explicitly re-enabled |  |  |
| Interrupt network during a read-only question | Error is visible; late response is not spoken; recovery remains bounded |  |  |
| Long spoken response, then Stop | Speech and watchdog are cancelled; no late restart occurs |  |  |
| Sign out while listening | Recognition and all voice resources return to zero |  |  |

## Performance evidence

After the ten-command sequence, record the following values from:

```javascript
window.__IHOS_PERFORMANCE__.snapshot()
```

| Signal | Threshold | Recorded value | Pass/fail |
| --- | --- | --- | --- |
| Maximum active recognition sessions | 1 |  |  |
| Voice command p95 | No more than 750 ms |  |  |
| Core render p95 | No more than 50 ms |  |  |
| API read p95 | No more than 1,500 ms |  |  |
| API server-error rate | Below 1% |  |  |
| Final recognition resources | All 0 after Stop |  |  |
| Final restart timers | 0 after Stop |  |  |
| Final speech watchdogs | 0 after Stop |  |  |
| Final pending requests | 0 after Stop |  |  |

## Acceptance decision

- Overall result: Pending
- Blocking observations:
- Evidence attachment or screenshot location:
- Tester signature:
- Approver:
- Approval date:

Change the overall result to **Passed** only when the device record is
complete, every command and lifecycle check passes, all thresholds pass, and
the evidence location is recorded. A failed or incomplete record keeps the
voice feature disabled for release.
