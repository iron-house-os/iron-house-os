# Version 1.0 staging performance and lifecycle observability

## Control record

- Parent issue: #85
- Work item: #87
- Branch: `sprint1/performance-observability`
- Dependency: PR #91, `sprint1/voice-stability-gate`
- Production baseline: Build 237 at `55afaa689603263c1ad415436e90cce6679808c3`
- Approval gate: human approval before merge; no production enablement

## Containment and privacy

Frontend collection is active in Vite development mode or when this build-time flag is explicitly enabled:

```text
VITE_PERFORMANCE_OBSERVABILITY_ENABLED=true
```

The Docker build default is `false`. Do not add the flag to `/etc/iron-house-os/production.env` or enable it in a production image without separate approval.

The browser collector keeps at most 100 duration samples in memory. It records only:

- aggregate request counts, outcome, and duration;
- aggregate React commit counts and render duration for the fixed `core-modules` profiler;
- recognizer starts, restarts, failures, active-session high-water mark, and command duration;
- current voice resource counts for recognition, restart timers, speech watchdogs, and requests.

It does not record request URLs, query strings, request or response bodies, transcripts, assistant responses, credentials, user identifiers, project identifiers, filenames, or supplier information. Nothing is transmitted or persisted.

When enabled, an operator can inspect the in-memory snapshot in the browser console:

```javascript
window.__IHOS_PERFORMANCE__.snapshot()
```

## Baseline recorded on 2026-07-29

The implementation branch produced this local automated baseline:

| Gate | Baseline |
| --- | --- |
| Backend Ruff | Passed |
| Backend pytest | 171 passed in 11.34 seconds; one existing Pydantic warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | 15 files, 45 tests passed in 4.52 seconds |
| Ten-command mocked iPad lifecycle | Passed; maximum active recognition sessions = 1 |
| Background/pagehide cleanup | Passed; all four tracked voice resources = 0 |
| Bounded retry | Passed; 5 retry attempts, exponential delay capped at 4 seconds, then fail closed |
| Production frontend build | Passed in 0.92 seconds |
| JavaScript bundle | 633.13 kB minified, 156.77 kB gzip |
| CSS bundle | 26.01 kB minified, 5.82 kB gzip |

The existing JavaScript chunk warning above 500 kB remains. This work does not change the Version 1.0 visual design or introduce code splitting.

Live staging API and device timings remain evidence to collect after the isolated staging URL and credentials exist.

## Regression thresholds

These thresholds are the Version 1.0 staging gate. A breach requires investigation and recorded approval before release:

| Signal | Threshold |
| --- | --- |
| Active recognition sessions | Never above 1 |
| Stop, logout, unmount, hidden tab, or pagehide | Recognition, restart timer, speech watchdog, and pending request all return to 0 |
| Consecutive recognition recovery | No more than 5 retries; delay no more than 4,000 ms |
| Local voice-navigation command p95 | No more than 750 ms on the physical acceptance iPad |
| Read-only API request p95 | No more than 1,500 ms on isolated staging |
| API server-error rate | Below 1% during the staging acceptance run |
| Core render p95 | No more than 50 ms on the physical acceptance iPad |
| JavaScript bundle | No more than 650 kB minified until a separate code-splitting change is approved |

## Lifecycle audit

- Recognition construction is guarded by the current active-session reference.
- Every recognition stop, end, error, Apple one-shot result, and unmount path detaches all handlers.
- Restart scheduling always clears the previous timer before creating one.
- Speech creation always cancels and detaches the previous utterance and watchdog.
- Voice requests use one abort controller and ignore late responses after cancellation.
- `visibilitychange` and `pagehide` fail closed by disabling voice and releasing resources.
- Both background listeners are removed when the provider unmounts.
