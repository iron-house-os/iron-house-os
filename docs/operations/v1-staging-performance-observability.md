# Version 1.0 staging performance observability

## Control record

- Parent issue: #85
- Work item: #87
- Original branch: `sprint1/performance-observability`
- Voice-control lifecycle telemetry: retired by owner decision under issue #88
- Production approval: still required separately

## Containment and privacy

Frontend collection is active in Vite development mode or when this build-time flag is explicitly enabled:

```text
VITE_PERFORMANCE_OBSERVABILITY_ENABLED=true
```

The Docker build default is `false`. Do not add the flag to `/etc/iron-house-os/production.env` or enable it in a production image without separate approval.

The browser collector keeps at most 100 duration samples in memory. It records only:

- aggregate request counts, outcomes, and durations; and
- aggregate React commit counts and render durations for the fixed `core-modules` profiler.

It does not record request URLs, query strings, request or response bodies, assistant prompts or responses, credentials, user identifiers, project identifiers, filenames, supplier information, microphone data, or transcripts. Nothing is transmitted or persisted.

When enabled, an operator can inspect the in-memory snapshot in the browser console:

```javascript
window.__IHOS_PERFORMANCE__.snapshot()
```

## Current regression thresholds

These thresholds apply to staging. A breach requires investigation and recorded approval before release:

| Signal | Threshold |
| --- | --- |
| Read-only API request p95 | No more than 1,500 ms on isolated staging |
| API server-error rate | Below 1% during the staging acceptance run |
| Core render p95 | No more than 50 ms on the physical acceptance device |
| JavaScript bundle | Must not exceed the current `main` baseline without investigation; the retirement candidate is 752.11 kB minified versus 766.61 kB on `main` |

## Voice-control retirement

The former voice-control lifecycle counters, command-duration samples, recognizer resource tracking, and physical voice-acceptance thresholds were removed with the voice-control system. Historical baselines remain in the associated build records as audit evidence only; they are not current release requirements.
