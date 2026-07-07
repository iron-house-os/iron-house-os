#!/usr/bin/env python3
"""Iron House Build Agent.

This runner is intentionally conservative. It reads the build queue, selects the
highest-priority open task, runs a configurable build command, runs checks, and
leaves GitHub branch/PR creation to the workflow shell.

The AI/code-generation step is pluggable through BUILD_AGENT_COMMAND. This keeps
secrets and model/provider choices outside the repo.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "automation" / "build-queue.json"
OUTPUT_PATH = ROOT / "automation" / "build-agent-output.json"


def main() -> int:
    queue = _read_json(QUEUE_PATH)
    task = _select_next_task(queue)
    if task is None:
        _write_json(OUTPUT_PATH, {"status": "idle", "message": "No open build tasks."})
        print("No open build tasks.")
        return 0

    print(f"Selected task: {task['id']} - {task['title']}")
    command = os.getenv("BUILD_AGENT_COMMAND")
    if command:
        _run(command, env={"IRON_HOUSE_BUILD_TASK": json.dumps(task)})
    else:
        _write_task_prompt(task)

    check_command = os.getenv("BUILD_AGENT_CHECK_COMMAND", "python automation/run_mvp_checks.py")
    check_result = _run(check_command, check=False)

    status = "completed" if check_result == 0 else "checks_failed"
    _write_json(
        OUTPUT_PATH,
        {
            "status": status,
            "task": task,
            "check_command": check_command,
            "check_exit_code": check_result,
        },
    )
    return check_result


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _select_next_task(queue: dict[str, Any]) -> dict[str, Any] | None:
    open_tasks = [task for task in queue.get("tasks", []) if task.get("status") == "open"]
    if not open_tasks:
        return None
    return sorted(open_tasks, key=lambda task: int(task.get("priority", 9999)))[0]


def _write_task_prompt(task: dict[str, Any]) -> None:
    prompt_path = ROOT / "automation" / "next-build-task.md"
    criteria = "\n".join(f"- {item}" for item in task.get("acceptance_criteria", []))
    prompt_path.write_text(
        f"# Next Iron House Build Task\n\n"
        f"## {task['title']}\n\n"
        f"Task ID: `{task['id']}`\n\n"
        f"Priority: {task.get('priority')}\n\n"
        f"{task.get('summary', '')}\n\n"
        f"## Acceptance Criteria\n\n{criteria}\n",
        encoding="utf-8",
    )
    print(f"No BUILD_AGENT_COMMAND configured. Wrote task prompt to {prompt_path}.")


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
