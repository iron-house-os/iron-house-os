# Iron House OS — full repository audit (2026-08-08)

Full-codebase audit covering `backend/`, `frontend/`, `database/`, `docker/`, `tests/`,
`.github/workflows/`, `ops/`, `scripts/`, `automation/`, `agents/`, and `docs/`. Findings are
ordered by priority: **critical** (real risk, fix first), **structural** (should fix, not
urgent), then **minor** (cleanup/consistency). Each finding names the file(s) involved.

Several items in the starting brief for this audit turned out to need correction once the
actual deploy tooling was read end to end — those corrections are called out inline so they
aren't re-litigated later.

## Critical

1. **No IP-based rate limiting on login — only per-account lockout.**
   `backend/app/services/auth.py` locks a given email after `LOGIN_MAX_FAILED_ATTEMPTS`, but
   nothing throttles by IP or globally. An attacker can mass-lock arbitrary employee accounts
   (denial of service via deliberate lockout) or spread slow credential guesses across many
   accounts to stay under each account's threshold. Add IP/global rate limiting in front of
   `/auth/login` (e.g. a `slowapi` middleware or an nginx-level limit in
   `ops/digitalocean/nginx-live.conf`).

2. **Recurring production backups are not guaranteed to run.**
   `scripts/scheduled_backup.sh` and the `ops/systemd/ihos-backup.timer` unit are correctly
   built, but **no automated script installs or enables that timer**. `ops/digitalocean/
   bootstrap-host.sh` and `ops/digitalocean/cloud-init.yaml` enable `docker` and `nginx` via
   systemd but never touch `ihos-backup.timer`, and `docs/builds/BUILD_212.md` says outright:
   "Example systemd service and timer units live in `ops/systemd/`. They are templates only
   and are not installed or enabled automatically." `ops/digitalocean/cutover.sh` only takes a
   one-off pre/post-cutover snapshot at deploy time — nothing guarantees a daily backup between
   deploys unless an operator manually ran the install step in `docs/deployment.md` on the
   droplet. **Action: confirm on `iron-house-os-prod-1` whether `ihos-backup.timer` is actually
   installed and enabled (`systemctl list-timers ihos-backup.timer`); if not, install it.**

   Correction to the original brief: this is *not* evidence that production storage is
   silently running on local disk with no S3. Every real deploy path in the repo
   (`ops/digitalocean/cutover.sh`, invoked directly or via `ops/deploy-agent/deploy.sh`) hard-
   fails unless `IHOS_STORAGE_BACKEND=s3`, `IHOS_STORAGE_S3_BUCKET`, and
   `IHOS_BACKUP_S3_BUCKET` are all set and the buckets pass `scripts/verify_s3_targets.sh`
   (private, versioned, encrypted, correct region). `.env.production.example` being blank is
   just the example template. The real, confirmed gap is narrower: the *recurring* backup
   cadence, not the *existence* of S3 storage.

3. **Backend has no startup guard against insecure config defaults.**
   `backend/app/core/config.py` defaults `secret_key` to `"change-me-in-development"` and
   `session_cookie_secure` to `False`, with no validator that hard-fails startup in a
   non-development environment if either is left at its default. If `SECRET_KEY` or
   `SESSION_COOKIE_SECURE` were ever missing from the environment the app is actually launched
   with, session JWTs (`app/services/auth.py`) would be signed with a publicly known key —
   full authentication bypass. Today this is mitigated at the deploy layer:
   `docker-compose.production.yml` declares `SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is
   required}` (fails closed) and defaults `SESSION_COOKIE_SECURE` to `true`. But the
   application itself has no defense-in-depth against running any other way (bare container,
   future compose refactor that drops the `:?required` guard, etc). Add an explicit `Settings`
   validator that refuses to start in production if `secret_key` is unset/default or
   `session_cookie_secure` is falsy.

4. **Verify the GitHub `production` Environment actually has required-reviewer protection.**
   `.github/workflows/finish-approved-production-deploy.yml` → `production-deploy.yml` is a
   real, working path from a push on `main` to a live production cutover. On inspection it is
   narrowly scoped — hardcoded to one historical release SHA
   (`55295263d861e60c535cc0b41185dcd8b18ae4e8`, matching commit `5529526` — "Make production
   cutover script executable"), only re-triggers if someone edits and pushes that exact
   workflow file, and `production-deploy.yml` declares `environment: production`. Whether that
   is a real human gate depends entirely on a GitHub-side setting (required reviewers on the
   `production` Environment) that isn't visible in code. **Action: check Settings → Environments
   → production on github.com/iron-house-os/iron-house-os and confirm required reviewers are
   configured.** If they aren't, anyone with push access to `main` (including the scheduled
   `build-agent.yml` bot, which has `contents: write, pull-requests: write`) could in principle
   drive a production cutover by editing that one workflow file.

## Structural

5. **`ops/digitalocean/nginx-live.conf` is hand-edited, not templated.**
   Confirms the original brief: `nginx-staging.conf.template` uses `${IHOS_STAGING_HOST}`
   substitution, but `nginx-live.conf` hardcodes `os.ironhousecivil.com` twice plus the cert
   paths. Recommend templating it the same way and generating it in
   `ops/digitalocean/production-deploy-wrapper.sh`/`cutover.sh` at deploy time, so a future
   domain or cert-path change is a variable edit instead of a hand edit to a file that's easy
   to typo under time pressure.

6. **Inconsistent client-side role-gating on financial data.**
   `frontend/src/pages/GoogleCalendarPage.tsx` correctly redirects non-admin/ops-manager users
   client-side, but `frontend/src/pages/FinancialControlPage.tsx` has no role check in the UI
   despite its own copy calling itself "management-only" — any authenticated non-viewer role
   can load the page shell. `frontend/src/App.tsx` only branches routes on `viewer` vs.
   everyone else. Backend RBAC (`backend/app/services/access_control.py`, applied at the
   router level in `backend/app/api/v1/router.py`) is centralized and looks solid, so this is
   very likely UI-only exposure rather than a real data leak — but it should be verified that
   every `/finance` endpoint the page calls is actually gated server-side, and the frontend
   route should get the same role check pattern used on the calendar page for defense in
   depth and consistency.

7. **Two disconnected in-repo automation/orchestration systems.**
   `automation/` (`autonomous_dispatcher.py`, `autonomous_foreman_v2.py`, `build-queue.json`)
   is a lighter-weight, provider-neutral "pick next task, hand to `IH_CODER_COMMAND`" dispatcher
   last touched 2026-07-25. `ops/agent/` is a separate, more mature multi-agent orchestrator
   with a SQLite job queue, per-job worktrees, GitHub-issue-label intake, and a dashboard
   (`agents/README.md`, `docs/agent-platform.md`), under active development through the most
   recent builds. Neither reads the other's state (`ops/agent/` never references
   `automation/build-queue.json`). Recommend picking one as canonical — `ops/agent/` looks like
   the active system — and either retiring `automation/`'s dispatcher or explicitly documenting
   why both exist.

   Correction to the original brief (item 6): `ops/agent` and `ops/deploy-agent` are **not**
   related to the ChatGPT Business workspace agents (Tender Scout, IHOS COO Agent, etc.).
   They're an internal CI/build-automation framework for engineering work on this repo and
   `Dumper`. The ChatGPT workspace agents are business-operations agents living outside this
   repo entirely. No reconciliation needed there — the actual duplication is the one above,
   between `automation/` and `ops/agent/`.

8. **Two separately-maintained, conflicting roadmap documents.**
   Root `ROADMAP.md` is badly stale — its "Next Product Builds" section lists "Build 25–28"
   and its "Current Completed Core" list (dashboard, RFQ builder, quote comparison, etc.)
   predates the actually-shipped feature set, which per `docs/builds/` runs through Build 240
   (Google Calendar) and includes field operations, meeting minutes, employee onboarding,
   equipment/rate sheets, and a full backups/receipt workflow. `Documentation/
   IRON_HOUSE_OS_ROADMAP.md` is a different, longer (292-line) document covering estimating
   assumptions and supplier defaults. Anyone landing on the root `ROADMAP.md` gets a
   materially wrong picture of what's built. Recommend either refreshing `ROADMAP.md` from
   `docs/builds/` history or removing it in favor of one canonical roadmap location.

9. **`frontend/package.json` pins most dependencies to `"latest"`** instead of semver ranges
   (react, react-dom, react-router-dom, lucide-react, most devDependencies). The lockfile
   currently resolves to real versions, but any lockfile regen or `npm install` without
   `--frozen-lockfile` will silently pull whatever is newest — a reproducibility and
   supply-chain risk for a single-droplet deployment with no staged rollout capacity. Pin real
   version ranges.

10. **Legacy `database/schema.sql` and `database/seed.sql` are still in the repo**, explicitly
    marked "Legacy reference only... Do not mount this file into a new database or use it for
    production upgrades," and confirmed unreferenced by any compose file, Dockerfile, or
    script. `seed.sql` also defines a plaintext default admin (`admin@ironhouse.local`) that
    could mislead a future contributor into thinking it's a real bootstrap path — the actual,
    correct bootstrap is `BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD` env vars via
    `app.db.bootstrap_admin`. Delete these files or move them under `docs/` clearly marked
    historical.

11. **Docker hardening gaps**, low urgency given the single-tenant, single-droplet deployment
    model, but worth a pass: `backend/Dockerfile` and `frontend/Dockerfile` run as root (no
    `USER` directive); none of the three compose files (`docker-compose.yml`,
    `docker-compose.staging.yml`, `docker-compose.production.yml`) set CPU/memory limits, so
    one runaway container (OCR/backend under load) can take down Postgres and nginx on the
    same 2 vCPU / 4 GiB droplet; base images (`postgres:16-alpine`, `node:22-alpine`,
    `nginx:1.27-alpine`, `python:3.12-slim`) are pinned by mutable tag, not digest.

12. **`tests/agent/` may not be wired into CI.** `ci.yml` and `release-readiness.yml` only run
    `pytest` from `backend/` (which picks up `tests/backend/` via `testpaths`). No workflow
    step was found that targets `tests/agent/` (~900 lines covering the deploy-agent's
    apparmor, dashboard, install, and registration behavior). If nothing else runs it, that
    suite is currently unenforced. Confirm and wire it in if not.

13. **Google Calendar OAuth token encryption key derivation is weak.**
    `backend/app/services/google_calendar.py` builds the Fernet cipher by SHA-256-hashing
    `GOOGLE_CALENDAR_TOKEN_ENCRYPTION_KEY` rather than requiring a proper base64 Fernet key,
    and there's no key-rotation story for already-encrypted token columns
    (`backend/app/models/calendar.py`). Not exploitable today since the feature is disabled by
    its kill switch, but should be hardened before `GOOGLE_CALENDAR_ENABLED=true` ever flips
    to `true` in production.

14. **A few large, multi-responsibility files worth splitting as they keep growing:**
    `backend/app/services/field_operations.py` (880 lines), `backend/app/api/v1/routes/
    google_calendar.py` (512 lines, mixes persistence/business rules/HTTP client logic),
    `frontend/src/pages/RFQBuilderPage.tsx` (1150 lines), `frontend/src/pages/
    EmployeePortalPage.tsx` (756 lines, also houses three other portal components),
    `frontend/src/contexts/HandsFreeVoiceContext.tsx` (682 lines).

15. **Uneven test coverage on the frontend.** 22 test files against 31 pages. Money/approval
    flows are covered (`FinancialControlPage.test.tsx`, `BackupsPage.test.tsx`,
    `ReceiptCapturePanel.test.tsx`), but `SettingsPage.tsx` (admin/identity governance),
    `PasswordRecoveryPage.tsx`, `SupplierDatabasePage.tsx`, `PurchaseOrderRequestPage.tsx`, and
    `EquipmentPage.tsx` have none. The 5 Playwright e2e specs don't cover login/auth or the
    finance approval workflow.

16. **`docker-compose.yml` (dev only) binds Postgres to `0.0.0.0:5432`** with a hardcoded weak
    password (`iron_house_dev`). Fine for a fully local machine; a real exposure if this
    compose file is ever run on a shared or cloud dev box. Staging/production correctly omit
    the host port publish.

## Minor / low urgency

17. **Embedded OpenAI dependency inside the app itself.** `OPENAI_CHAT_MODEL`/
    `OPENAI_TRANSCRIPTION_MODEL` power in-app chat and meeting-minutes transcription — a
    second, separate OpenAI dependency living in the company's own infrastructure, distinct
    from the ChatGPT workspace agents this effort started from. Not urgent, just worth the
    business being aware it exists as a vendor dependency with its own kill switches
    (`IRON_HOUSE_CHAT_ENABLED`, `MEETING_MINUTES_ENABLED`).

18. **Google Calendar integration is fully built but intentionally disabled** —
    correction to the original brief: this is a deliberate production kill switch
    (`GOOGLE_CALENDAR_ENABLED=false`), not a half-finished or forgotten feature. Build 240's
    docs describe complete governance controls (scope-limited OAuth, encrypted tokens,
    confirmation-gated event creation, audit metadata). The redirect URI in
    `.env.production.example` (`https://os.ironhousecivil.com/...`) is also already correct —
    it points at the confirmed, working production domain, not a stale one. No action needed
    beyond addressing item 13 above before flipping the switch.

19. **`python-jose[cryptography]` is a lightly-maintained JWT library** with a history of
    algorithm-confusion CVEs in older versions. Low risk today since only HS256 is used and
    the algorithm is hardcoded server-side, but worth migrating to `PyJWT` eventually.

20. **GitHub Actions are pinned to major-version tags (`@v4`/`@v5`), not commit SHAs.** Good
    hygiene relative to `@main`, but tag pinning is still weaker than SHA pinning for
    supply-chain integrity.

21. **`build-agent.yml` runs unattended on a schedule** (weekdays 13:00 UTC) with
    `contents: write, pull-requests: write`, executing `automation/iron_house_build_agent.py`.
    Confirm its output PRs still go through the same `ci.yml`/branch-protection review as
    human-authored PRs (this is very likely already true via branch protection, just wasn't
    directly verifiable from workflow YAML alone).

22. **Form drafts cached in plain `localStorage`** on shared/kiosk field devices
    (`frontend/src/components/DailyTimesheetWorkflow.tsx`,
    `frontend/src/pages/SafetyOperationsPage.tsx`/`SafetyProgramPage.tsx`). Not secrets, but
    unencrypted and persists across users of the same device.

## What's already solid (no action needed)

- `ops/digitalocean/cutover.sh` is a well-designed, defense-in-depth deploy gate: exact-SHA
  checkout, clean-tree check, checksummed evidence bundle, protected-secret-file permission
  check, DNS verification against the droplet's own public IP, private/versioned/encrypted S3
  target verification, fail-closed maintenance page during the window, and automatic rollback
  to maintenance on any post-cutover failure. No need to duplicate or rebuild this.
- Backend RBAC is centralized well (`access_control.py` + router-level enforcement) rather than
  scattered per-route checks; password hashing is solid (pbkdf2_sha256, 600k iterations,
  enumeration-resistant); 17 Alembic migrations are linear with real `downgrade()`s and are
  cross-checked at runtime via `/readiness`.
- `backend/app/services/file_storage.py` correctly guards against path traversal, randomizes
  filenames, streams size limits, and verifies S3 read-back via SHA-256 — no issues found.
- `scripts/backup.sh`/`restore.sh`/`backup_retention.py` are correctly built: atomic writes,
  manifest verification before delete, a safety backup taken before restore, and a
  `keep_minimum` floor respected before age/count-based pruning.
- Frontend has no XSS/eval/hardcoded-secret findings, uses httpOnly cookies (not localStorage)
  for auth, and TypeScript strict mode is genuinely enforced (zero `any` usage found
  project-wide).
- No hardcoded secrets, API keys, or private key material were found anywhere in the scanned
  source tree.

## Domain note (do not act on)

`os.ironhousecivil.com` remains the confirmed, DNS-correct production domain — this audit did
not touch it. `os.ironhousecontracting.com` still has no public DNS and was not added to any
nginx config or cert request.
