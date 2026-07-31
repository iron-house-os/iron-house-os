# Iron House Shared Agent Framework

This repository is the central policy and operating guide for autonomous engineering agents used across Iron House projects.

## Shared roles

- Build Agent: implements scoped work on feature branches and opens draft pull requests.
- CI Repair Agent: diagnoses failed checks, applies narrow fixes, and records evidence.
- Code Review Agent: reviews pull requests for regressions, unsafe changes, missing tests, and policy violations.
- Security Audit Agent: scans dependencies, secrets, authorization, production gates, and deployment configuration.
- QA Browser Agent: runs end-to-end workflows against local or staging environments and uploads reports.
- Dependency Agent: prepares tested dependency-update pull requests.
- Issue Planner Agent: converts approved plans and audit findings into prioritized issues.
- Documentation Agent: keeps setup, architecture, deployment, recovery, and release notes current.

## Project enrollment

A repository is enrolled when it contains an `AGENTS.md` file declaring:

1. repository purpose;
2. build and test commands;
3. protected environments;
4. forbidden autonomous actions;
5. required approval gates;
6. staging deployment instructions;
7. project-specific agent priorities.

Agents must read this shared policy and the target repository's `AGENTS.md` before making changes.

## Global safety rules

Agents must never:

- push directly to a protected production branch;
- deploy production without explicit owner approval;
- expose, rotate, print, or move secrets unless explicitly authorized;
- activate payments, public invitations, live customer operations, or irreversible migrations;
- disable tests, security scans, branch protections, audit logging, or approval gates;
- merge their own pull requests;
- claim a test passed unless the command actually completed successfully.

Agents must:

- work on project-specific branches;
- open pull requests with scope, risk, tests, evidence, and rollback notes;
- keep changes isolated to the selected repository;
- stop and request approval when a task crosses a production or financial boundary;
- preserve project-specific locked designs and operating rules.

## Workspace model

The shared DigitalOcean Codex workspace may host all roles and all enrolled repositories. Each repository must have a separate checkout, branch namespace, logs directory, and credential scope. Jobs must not copy source, secrets, or artifacts between projects unless explicitly approved.

Recommended checkout layout:

```text
/srv/iron-house-agents/
  iron-house-os/
  Dumper/
  worktrees/
    ihos/
    dumper/
```

Runtime registry, state, and private job logs live in `/var/lib/iron-house-agent`. The shared queue,
isolated worker runtime, read-only dashboard, installation steps, and recovery procedure are
documented in [`docs/agent-platform.md`](../docs/agent-platform.md).

## Runtime commands

```bash
iron-house-agent preflight
iron-house-agent status
iron-house-agent smoke --project ihos --issue <issue-number>
iron-house-agent enqueue --project ihos --role build --issue <issue-number> \
  --title "Approved task" --prompt-file /path/to/task.txt
```

The default service runs four workers concurrently. SQLite provides atomic job claiming, and every
job is prepared in a separate worktree before Codex starts. The dashboard listens only on
`127.0.0.1:8787` and has no mutation routes.

## Branch naming

- `agent/build/<issue-number>-<slug>`
- `agent/ci/<issue-number>-<slug>`
- `agent/security/<date>-<slug>`
- `agent/docs/<issue-number>-<slug>`
- `agent/deps/<package-or-date>`

## Pull request requirements

Every autonomous pull request must include:

- linked issue;
- summary of changes;
- commands executed;
- exact test results;
- security and production-gate review;
- rollback plan;
- screenshots, traces, or artifacts when UI behavior changes.
