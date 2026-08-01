# Iron House autonomous development platform

## Objective

Run reusable development agents for Iron House OS, Dumper, and future Iron House repositories from the shared non-production DigitalOcean workspace. Every job is issue-linked, isolated in its own Git worktree, and prevented from deploying production.

## Current operating state

- Owner: Iron House development operations
- Priority: High
- Status: Active on the shared non-production build workspace
- Approval gate: Jeremie Peters must explicitly approve any production deployment; the agent platform cannot grant that approval
- System of record: `ops/agent/projects.json`, the SQLite job database, GitHub issues, and draft pull requests
- Production systems: out of scope

## Components

| Component | Purpose | Default location |
| --- | --- | --- |
| Project registry | Enrolled repositories and immutable production gate | `/var/lib/iron-house-agent/projects.json` |
| Job store | Queue, workers, timestamps, outcomes, and history | `/var/lib/iron-house-agent/jobs.sqlite3` |
| Logs | One private JSONL log per Codex job | `/var/lib/iron-house-agent/logs/` |
| Worktrees | One isolated feature branch checkout per job | `/srv/iron-house-agents/worktrees/` |
| Dashboard | Read-only queue, worker, history, and repository health | `http://127.0.0.1:8787` |
| GitHub intake | Explicitly labelled issue discovery and duplicate suppression | `iron-house-agent.service` |
| Service | Four concurrent worker loops, issue intake, and dashboard | `iron-house-agent.service` |

The dashboard binds to loopback and exposes no write endpoint. Access it remotely through an SSH tunnel rather than a public listener.

## One-time authentication checkpoint

Run device-code authentication as the unprivileged agent user. Open the URL printed by Codex in a browser, enter the one-time code, and complete the account flow. Never paste the code or cached credential into Git, a ticket, or chat.

```bash
sudo -u ih-agent -H codex login --device-auth
sudo -u ih-agent -H codex login status
sudo -u ih-agent -H gh auth status
```

Codex authentication is stored under the `ih-agent` account and reused by non-interactive jobs. The worker environment intentionally removes `OPENAI_API_KEY`, `CODEX_API_KEY`, and `GH_TOKEN`; use the saved Codex and GitHub CLI sessions. Standard jobs enable network access inside the workspace-write sandbox so they can fetch dependencies, push feature branches, and open draft pull requests. Non-destructive smoke jobs explicitly disable sandbox network access.

## Install and verify

From `/srv/iron-house-agents/iron-house-os` on the build droplet:

```bash
git switch main
git pull --ff-only
sudo bash ops/agent/install.sh
sudo -u ih-agent -H iron-house-agent preflight
sudo -u ih-agent -H iron-house-agent smoke --project ihos --issue 107
```

The smoke command creates an isolated local feature branch, runs read-only repository inspection through `codex exec`, and records the result. It does not change files, commit, push, open a pull request, install dependencies, or contact production.

To validate an unmerged feature branch from a detached review worktree without installing the service, run:

```bash
sudo -u ih-agent -H bash ops/agent/smoke-pr.sh
```

The wrapper uses private state and worktree directories under the `ih-agent` home directory. Optional positional arguments select another registered project and issue number.

Start the service only after preflight and the smoke test pass:

```bash
sudo systemctl enable --now iron-house-agent.service
systemctl --no-pager --full status iron-house-agent.service
curl --fail http://127.0.0.1:8787/healthz
```

## Queue work

Every job requires an existing GitHub issue number and an enrolled project. Prompts containing common API-key or token forms are rejected.

```bash
sudo -u ih-agent -H iron-house-agent enqueue \
  --project ihos \
  --role build \
  --issue 107 \
  --title "Complete issue 107 acceptance criteria" \
  --prompt-file /path/to/approved-task.txt
```

Supported roles:

- `build`
- `ci-repair`
- `code-review`
- `qa-browser`
- `security-audit`
- `dependency-update`
- `documentation`
- `issue-planning`

Standard jobs instruct Codex to work only on the generated feature branch, run relevant checks, commit and push the scoped change, and open a draft pull request. The agent is explicitly prohibited from merging or deploying production.

## Queue work from GitHub

The service polls registered repositories every 30 seconds without opening a public webhook. To approve an issue for intake, keep the issue open and apply:

1. `agent:ready`
2. exactly one role label:
   - `agent:build`
   - `agent:ci-repair`
   - `agent:code-review`
   - `agent:qa-browser`
   - `agent:security-audit`
   - `agent:dependency-update`
   - `agent:documentation`
   - `agent:issue-planning`

The issue title becomes the job title and the body becomes the task prompt. Adding `agent:ready` authorizes feature-branch work only; it never authorizes merge, production deployment, payment, invitation, or owner-only actions.

Each repository, issue number, and GitHub update revision is accepted at most once. Removing `agent:ready` stops new intake. To queue a corrected revision after a blocked or completed run, edit the issue and retain the required labels. The new GitHub update timestamp creates one new intake revision.

Run one immediate check without waiting for the service interval:

```bash
sudo -u ih-agent -H iron-house-agent intake-once
```

Ambiguous roles, missing repository policy, secret-like issue text, prohibited production actions, and GitHub authentication failures are recorded as blocked. Issue bodies and job prompts never appear in dashboard JSON.

## Register a future project

Before enrollment, the GitHub repository must contain an `AGENTS.md` file declaring its build/test commands, protected environments, forbidden actions, approval gates, staging instructions, and priorities.

Preview every validation without cloning, editing the registry, creating labels, or restarting the service:

```bash
sudo iron-house-agent-register --dry-run \
  --key future-project \
  --name "Future Project" \
  --repository iron-house-os/future-project \
  --directory future-project \
  --default-branch main
```

Run the same command without `--dry-run` to enroll and activate the project:

```bash
sudo iron-house-agent-register \
  --key future-project \
  --name "Future Project" \
  --repository iron-house-os/future-project \
  --directory future-project \
  --default-branch main
```

The single registration command verifies saved GitHub access, repository identity, default branch,
and the remote `AGENTS.md` before mutation. It clones through GitHub CLI, verifies the checkout
origin, creates the standard intake labels, atomically updates the private runtime registry, marks
intake health ready, restarts the non-production service, and checks the loopback health endpoint.
Re-running the exact registration is safe. Production deployment is always disabled. The tracked
`ops/agent/projects.json` remains an installation seed; runtime registration never dirties the
central repository checkout.

## Dashboard access

From a trusted workstation with SSH access to the build droplet:

```bash
ssh -L 8787:127.0.0.1:8787 ih-agent@178.128.231.173
```

Then open `http://127.0.0.1:8787`. The dashboard shows:

- configured agent roles and active workers;
- current jobs and feature branches;
- queued work;
- completed and failed build history;
- clean, dirty, blocked, missing, or unhealthy repository checkouts.
- GitHub intake source health, accepted revisions, and blocked reasons.

## Recovery and controls

```bash
sudo systemctl stop iron-house-agent.service
sudo -u ih-agent -H iron-house-agent status
journalctl -u iron-house-agent.service --since today --no-pager
sudo systemctl start iron-house-agent.service
```

Do not delete the job database or worktrees during incident review. Stop the service first, preserve `/var/lib/iron-house-agent`, and record the affected job ID and branch.

Key controls:

- The service runs as the dedicated unprivileged `ih-agent` user with `ProtectSystem=strict`,
  a private temporary directory, a restrictive umask, and only the agent workspace, state,
  Codex configuration, and GitHub CLI configuration writable. `NoNewPrivileges` is deliberately
  disabled because Codex must create its Bubblewrap user namespace; the service has no sudo access
  or added Linux capabilities.
- Build, CI repair, dependency, and documentation jobs are successful only after a new clean commit,
  a pushed issue-linked branch, and a verifiable open draft pull request exist. An explicit blocked
  Codex response fails the job even when the CLI exits zero.

- The service runs as `ih-agent`, not root.
- The dashboard is loopback-only and read-only.
- Each job receives a separate worktree and issue-linked branch.
- Worker subprocesses receive a restricted environment rather than inherited secret variables.
- Production deployment is rejected by registry validation.
- Dumper payment, invitation, owner-only, qualification, and live-load gates remain outside autonomous scope.
- No agent may approve or merge its own pull request.

## Failure modes

| Failure | Result | Recovery |
| --- | --- | --- |
| Codex or GitHub login expires | Workers report `blocked`; queued jobs remain queued | Re-authenticate as `ih-agent`, run `preflight`, restart service |
| Repository lacks `AGENTS.md` | Job or registration fails closed | Add and review the project policy before retrying |
| GitHub intake is blocked | No issue is enqueued from the affected repository | Review the dashboard reason, repair authentication or labels, then edit the issue to create a new revision |
| Issue has no role or multiple roles | The issue revision is retained as `blocked` | Apply exactly one supported role label and edit the issue before retrying |
| Issue contains secret-like or prohibited production text | The issue revision is retained as `blocked` | Remove the sensitive or prohibited instruction; use saved credentials and the separate owner-approved production workflow |
| Worker task fails | Job is retained as `failed` with branch and log path | Inspect evidence and queue a narrow follow-up issue-linked job |
| Checkout is dirty | Dashboard reports `dirty` | Review ownership of the changes; do not discard them automatically |
| Dashboard unavailable | Workers may continue; health endpoint fails | Check service status and journal; dashboard has no job-control authority |
| Production request enters a prompt | Agent policy forbids the action | Stop and require explicit owner-approved production workflow outside this platform |

## Build note

The next durable improvement should add authenticated notifications for failed or blocked jobs after the local service and smoke test are verified. Notifications must not include prompts, logs, tokens, or other sensitive content.
