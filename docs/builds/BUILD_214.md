# Build 214 — Browser, mobile, and accessibility release gate

Build 214 adds a required Chromium gate to pull-request and `main` CI.

## Gate coverage

- Builds and serves the production frontend bundle.
- Exercises the sign-in transition into the authenticated dashboard shell.
- Runs at desktop Chrome and Pixel 7 viewport/device settings.
- Rejects horizontal viewport overflow and verifies the mobile navigation control.
- Runs axe rules tagged WCAG 2.0/2.1 A and AA and rejects serious or critical violations.
- Captures Playwright traces, screenshots, and an HTML report on failure; CI retains the report for 14 days.

API responses are intercepted with deterministic, non-production fixtures. This makes the browser gate repeatable and prevents CI from needing credentials or paid infrastructure. Backend authentication, authorization, and production-stack smoke coverage remain separate required gates.

## Local use

```bash
cd frontend
npm ci
npx playwright install chromium
npm run build
npm run test:e2e
```

The browser binaries are development/CI dependencies only and are not included in the production frontend image.
