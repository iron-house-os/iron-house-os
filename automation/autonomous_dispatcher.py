#!/usr/bin/env python3
"""Iron House Autonomous Development Dispatcher v1.

The dispatcher selects the next task from the build queue and hands it to an
external coder command configured through IH_CODER_COMMAND.

This keeps the repo provider-neutral. The coder command may be a local script,
Codex CLI, another coding agent, or a hosted runner. If no command is configured,
the dispatcher writes the selected task and exits successfully.
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
OUTPUT_PATH = ROOT / "automation" / "autonomous-output.json"
NEXT_TASK_PATH = ROOT / "automation" / "selected-task.json"
NEXT_PROMPT_PATH = ROOT / "automation" / "selected-task-prompt.md"


def main() -> int:
    queue = _read_json(QUEUE_PATH)
    task = _select_next_task(queue)
    if task is None:
        _write_json(OUTPUT_PATH, {"status": "idle", "message": "No open tasks."})
        print("No open tasks.")
        return 0

    prompt = _build_prompt(task)
    _write_json(NEXT_TASK_PATH, task)
    NEXT_PROMPT_PATH.write_text(prompt, encoding="utf-8")

    command = os.getenv("IH_CODER_COMMAND")
    if not command:
        _write_json(
            OUTPUT_PATH,
            {
                "status": "selected_task_only",
                "task": task,
                "message": "Set IH_CODER_COMMAND to enable autonomous code generation.",
                "selected_task_file": str(NEXT_TASK_PATH.relative_to(ROOT)),
                "prompt_file": str(NEXT_PROMPT_PATH.relative_to(ROOT)),
            },
        )
        print("Selected task only. IH_CODER_COMMAND is not configured.")
        print(prompt)
        return 0

    print(f"Running coder command for task {task['id']}")
    result = subprocess.run(
        command,
        shell=True,
        cwd=ROOT,
        check=False,
        env={
            **os.environ,
            "IH_SELECTED_TASK_JSON": json.dumps(task),
            "IH_SELECTED_TASK_FILE": str(NEXT_TASK_PATH),
            "IH_SELECTED_PROMPT_FILE": str(NEXT_PROMPT_PATH),
        },
    )
    status = "coder_completed" if result.returncode == 0 else "coder_failed"
    _write_json(
        OUTPUT_PATH,
        {
            "status": status,
            "task": task,
            "coder_exit_code": result.returncode,
            "selected_task_file": str(NEXT_TASK_PATH.relative_to(ROOT)),
            "prompt_file": str(NEXT_PROMPT_PATH.relative_to(ROOT)),
        },
    )
    return result.returncode


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


def _build_prompt(task: dict[str, Any]) -> str:
    criteria = "\n".join(f"- {item}" for item in task.get("acceptance_criteria", []))
    return f"""# Iron House OS Autonomous Build Task

Use MVP-first approach. Keep changes practical and small. Do not send emails, submit bids, spend money, approve contracts, or merge PRs.

## Task

ID: {task.get('id')}
Title: {task.get('title')}
Priority: {task.get('priority')}

## Summary

{task.get('summary', '')}

## Acceptance Criteria

{criteria}

## Expected Output

Modify the repository directly. Then let CI run tests and open a pull request for review.
"""


if __name__ == "__main__":
    sys.exit(main())
