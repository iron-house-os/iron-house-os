#!/usr/bin/env python3
"""Iron House Build Agent.

This runner is the build foreman. It reads the queue, selects the next task,
writes the exact GO prompt for ChatGPT, and runs fast checks.

When BUILD_AGENT_COMMAND is configured, it can hand the task to an external
coder. Without that command, it tells Jeremie exactly what to paste into ChatGPT.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "automation" / "build-queue.json"
OUTPUT_PATH = ROOT / "automation" / "build-agent-output.json"
PROMPT_PATH = ROOT / "automation" / "next-build-task.md"


def main() -> int:
    queue = _read_json(QUEUE_PATH)
    task = _select_next_task(queue)
    if task is None:
        _write_json(OUTPUT_PATH, {"status": "idle", "message": "No open build tasks."})
        print("No open build tasks.")
        return 0

    print(_go_line(task))
    command = os.getenv("BUILD_AGENT_COMMAND")
    if command:
        _run(command, env={"IRON_HOUSE_BUILD_TASK": json.dumps(task)})
    else:
        _write_go_prompt(task)

    check_command = os.getenv("BUILD_AGENT_CHECK_COMMAND", "python automation/run_mvp_checks.py")
    check_result = _run(check_command, check=False)

    status = "ready_for_chatgpt" if check_result == 0 else "checks_failed"
    _write_json(
        OUTPUT_PATH,
        {
            "status": status,
            "go_prompt_file": str(PROMPT_PATH.relative_to(ROOT)),
            "go_prompt": _chatgpt_prompt(task),
            "task": task,
            "check_command": check_command,
            "check_exit_code": check_result,
        },
    )
    print("NEXT CHATGPT PROMPT:")
    print(_chatgpt_prompt(task))
    return check_result


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _select_next_task(
    queue: dict[str, Any],
    issue_state_getter: Callable[[dict[str, Any]], str] | None = None,
) -> dict[str, Any] | None:
    open_tasks = [task for task in queue.get("tasks", []) if task.get("status") == "open"]
    if not open_tasks:
        return None

    get_issue_state = issue_state_getter or _github_issue_state
    current_tasks = []
    for task in open_tasks:
        _validate_issue_linked_task(task)
        if get_issue_state(task) == "open":
            current_tasks.append(task)

    if not current_tasks:
        return None
    return sorted(current_tasks, key=lambda task: int(task.get("priority", 9999)))[0]


def _validate_issue_linked_task(task: dict[str, Any]) -> None:
    required = ("id", "title", "repository", "github_issue_number", "github_issue_url")
    missing = [field for field in required if not task.get(field)]
    if missing:
        task_id = task.get("id", "unknown")
        fields = ", ".join(missing)
        raise ValueError(
            f"Open build task {task_id} is missing canonical GitHub fields: {fields}. "
            "Refusing to generate a stale prompt."
        )

    repository = str(task["repository"])
    issue_number = int(task["github_issue_number"])
    expected_url = f"https://github.com/{repository}/issues/{issue_number}"
    if task["github_issue_url"] != expected_url:
        raise ValueError(
            f"Open build task {task['id']} has a non-canonical GitHub issue URL. "
            f"Expected {expected_url}."
        )


def _github_issue_state(task: dict[str, Any]) -> str:
    repository = str(task["repository"])
    issue_number = int(task["github_issue_number"])
    api_url = f"https://api.github.com/repos/{repository}/issues/{issue_number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "iron-house-os-build-agent",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with urlopen(Request(api_url, headers=headers), timeout=15) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Could not verify GitHub Issue #{issue_number} for {repository}; "
            "refusing to generate a build prompt."
        ) from exc

    if "pull_request" in payload:
        raise RuntimeError(
            f"Configured queue target {repository}#{issue_number} is a pull request, not an issue."
        )

    state = payload.get("state")
    if state not in {"open", "closed"}:
        raise RuntimeError(
            f"GitHub Issue #{issue_number} for {repository} returned an invalid state."
        )
    return str(state)


def _write_go_prompt(task: dict[str, Any]) -> None:
    criteria = "\n".join(f"- {item}" for item in task.get("acceptance_criteria", []))
    PROMPT_PATH.write_text(
        f"# GO: {task['title']}\n\n"
        f"Paste this into ChatGPT:\n\n"
        f"```text\n{_chatgpt_prompt(task)}\n```\n\n"
        f"## Task\n\n"
        f"Task ID: `{task['id']}`\n\n"
        f"GitHub Issue: [#{task['github_issue_number']}]({task['github_issue_url']})\n\n"
        f"Priority: {task.get('priority')}\n\n"
        f"{task.get('summary', '')}\n\n"
        f"## Acceptance Criteria\n\n{criteria}\n",
        encoding="utf-8",
    )
    print(f"Wrote GO prompt to {PROMPT_PATH}.")


def _go_line(task: dict[str, Any]) -> str:
    return f"GO: {task['title']} ({task['id']})"


def _chatgpt_prompt(task: dict[str, Any]) -> str:
    return (
        f"GO. Continue only {task['repository']} GitHub Issue "
        f"#{task['github_issue_number']}: {task['title']}. "
        f"Canonical issue: {task['github_issue_url']}. Task ID: {task['id']}. "
        f"Summary: {task.get('summary', '')} "
        "Use an issue-linked branch and draft pull request. Preserve the locked Iron House "
        "visual design. Do not merge, deploy, or change production data, DNS, secrets, "
        "certificates, backups, or infrastructure without the applicable owner approval."
    )


def _run(command: str, *, env: dict[str, str] | None = None, check: bool = True) -> int:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, cwd=ROOT, env=merged_env, check=False)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
