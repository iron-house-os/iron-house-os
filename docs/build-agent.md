# Iron House Build Agent

## Purpose

The Iron House Build Agent is a conservative automation scaffold for moving Iron House OS forward from a GitHub queue.

It does not merge to main automatically. It creates a branch and opens a pull request for review.

## Workflow

1. Read `automation/build-queue.json`.
2. Select the highest-priority task with status `open`.
3. Run the optional command in `BUILD_AGENT_COMMAND`.
4. Run MVP checks.
5. Commit changed files to a branch.
6. Open a pull request.

## Files

- `automation/build-queue.json` — task queue
- `automation/iron_house_build_agent.py` — local/CI runner
- `automation/run_mvp_checks.py` — fast validation checks
- `.github/workflows/build-agent.yml` — scheduled/manual GitHub Action

## Local Use

From repo root:

```bash
python automation/iron_house_build_agent.py
```

Without `BUILD_AGENT_COMMAND`, the agent writes the next task prompt to:

```text
automation/next-build-task.md
```

To plug in an external code-generation command:

```bash
BUILD_AGENT_COMMAND='your-command-here' python automation/iron_house_build_agent.py
```

The selected task is passed through the environment variable:

```text
IRON_HOUSE_BUILD_TASK
```

## GitHub Actions Use

The workflow can run manually from GitHub Actions or on its weekday schedule.

Recommended repository secret:

```text
BUILD_AGENT_COMMAND
```

That command should:

- Read `IRON_HOUSE_BUILD_TASK`
- Modify code as needed
- Leave files changed in the working tree
- Avoid sending emails, spending money, submitting bids, or making commitments

The workflow then:

- Runs checks
- Commits changes
- Pushes a branch
- Opens a pull request

## Safety Rules

The Build Agent is allowed to:

- Generate code
- Modify docs
- Run tests
- Open pull requests

The Build Agent is not allowed to:

- Merge pull requests automatically
- Send external emails
- Submit bids
- Spend money
- Sign or approve contracts
- Make binding commitments

## Recommended MVP Command Strategy

For now, use the agent to create prompts and PRs. After the MVP is stable, connect a controlled code-generation command.

The safest first command is one that reads `automation/next-build-task.md`, generates a patch locally, and leaves it for review.
