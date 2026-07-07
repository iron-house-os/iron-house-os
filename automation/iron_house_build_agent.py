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
from typing import Any

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


def _select_next_task(queue: dict[str, Any]) -> dict[str, Any] | None:
    open_tasks = [task for task in queue.get("tasks", []) if task.get("status") == "open"]
    if not open_tasks:
        return None
    return sorted(open_tasks, key=lambda task: int(task.get("priority", 9999)))[0]


def _write_go_prompt(task: dict[str, Any]) -> None:
    criteria = "\n".join(f"- {item}" for item in task.get("acceptance_criteria", []))
    PROMPT_PATH.write_text(
        f"# GO: {task['title']}\n\n"
        f"Paste this into ChatGPT:\n\n"
        f"```text\n{_chatgpt_prompt(task)}\n```\n\n"
        f"## Task\n\n"
        f"Task ID: `{task['id']}`\n\n"
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
        "GO. Use Jeremie GPT mode. Continue Iron House OS MVP-first build. "
        f"Next task: {task['title']}. Task ID: {task['id']}. "
        f"Build it in GitHub and keep it practical. Summary: {task.get('summary', '')}"
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
