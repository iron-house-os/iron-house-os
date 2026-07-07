# Iron House Autonomous Development System v1

## Purpose

This system removes Jeremie from the prompt loop as much as the current repository tooling allows.

Instead of requiring Jeremie to paste prompts into ChatGPT, the repository can run an autonomous dispatcher from GitHub Actions or a local runner.

## Components Added

- `automation/autonomous_dispatcher.py`
- `automation/autonomous_config.json`

## How It Works

1. Reads `automation/build-queue.json`.
2. Selects the highest-priority task with status `open`.
3. Writes the selected task to `automation/selected-task.json`.
4. Writes a full coding prompt to `automation/selected-task-prompt.md`.
5. If `IH_CODER_COMMAND` is configured, runs that command.
6. Passes the selected task through environment variables.
7. Writes status to `automation/autonomous-output.json`.

## Required Secret

Create a GitHub repository secret:

`IH_CODER_COMMAND`

That command is the actual coding engine. It can point to a local script, a hosted coding runner, Codex CLI, or another AI coding tool that can read the selected task and modify the repository.

The dispatcher passes these environment variables to the command:

- `IH_SELECTED_TASK_JSON`
- `IH_SELECTED_TASK_FILE`
- `IH_SELECTED_PROMPT_FILE`

## Local Run

From the repository root:

`python automation/autonomous_dispatcher.py`

With a coder command:

`IH_CODER_COMMAND='your-coder-command' python automation/autonomous_dispatcher.py`

## GitHub Actions Setup

The workflow file could not be safely committed through the connector, so create this file manually in GitHub:

`.github/workflows/autonomous-development.yml`

It should run:

1. checkout
2. setup Python 3.12
3. setup Node 22
4. install backend dependencies
5. install frontend dependencies
6. run `python automation/autonomous_dispatcher.py`
7. run `python automation/run_mvp_checks.py`
8. show `automation/autonomous-output.json`

## Safety Boundaries

The dispatcher may select and hand off coding tasks.

It must not:

- send emails
- submit bids
- spend money
- approve contracts
- merge pull requests automatically
- make external commitments

## Current Limitation

The dispatcher is ready, but the actual code-writing command must still be connected through `IH_CODER_COMMAND`.

Once that command is configured, the loop becomes:

Build queue -> dispatcher -> coder command -> checks -> reviewable changes.
