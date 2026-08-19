import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "automation" / "iron_house_build_agent.py"
SPEC = importlib.util.spec_from_file_location("iron_house_build_agent", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
BUILD_AGENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_AGENT)


def _task(issue_number: int, *, priority: int = 100, status: str = "open") -> dict:
    return {
        "id": f"issue-{issue_number}",
        "priority": priority,
        "status": status,
        "repository": "iron-house-os/iron-house-os",
        "github_issue_number": issue_number,
        "github_issue_url": (
            f"https://github.com/iron-house-os/iron-house-os/issues/{issue_number}"
        ),
        "title": f"Issue {issue_number}",
        "summary": "A bounded issue-linked task.",
    }


def test_open_task_without_github_issue_reference_is_rejected() -> None:
    queue = {
        "tasks": [
            {
                "id": "legacy-open-task",
                "priority": 1,
                "status": "open",
                "title": "Legacy task",
            }
        ]
    }

    with pytest.raises(ValueError, match="canonical GitHub fields"):
        BUILD_AGENT._select_next_task(queue, lambda task: "open")


def test_superseded_tasks_are_not_selected() -> None:
    queue = {
        "tasks": [
            {
                "id": "legacy-task",
                "priority": 1,
                "status": "superseded",
                "title": "Legacy task",
            },
            _task(213, priority=2),
        ]
    }

    selected = BUILD_AGENT._select_next_task(queue, lambda task: "open")

    assert selected is not None
    assert selected["github_issue_number"] == 213


def test_closed_issue_linked_task_returns_idle() -> None:
    queue = {"tasks": [_task(213)]}

    assert BUILD_AGENT._select_next_task(queue, lambda task: "closed") is None


def test_lowest_priority_open_issue_is_selected() -> None:
    queue = {"tasks": [_task(214, priority=214), _task(213, priority=213)]}

    selected = BUILD_AGENT._select_next_task(queue, lambda task: "open")

    assert selected is not None
    assert selected["github_issue_number"] == 213


def test_prompt_includes_canonical_issue_and_production_controls() -> None:
    prompt = BUILD_AGENT._chatgpt_prompt(_task(213))

    assert "iron-house-os/iron-house-os GitHub Issue #213" in prompt
    assert "https://github.com/iron-house-os/iron-house-os/issues/213" in prompt
    assert "draft pull request" in prompt
    assert "Do not merge, deploy" in prompt


def test_checked_in_queue_supersedes_legacy_open_builds() -> None:
    queue = json.loads((ROOT / "automation" / "build-queue.json").read_text())
    tasks = {task["id"]: task for task in queue["tasks"]}

    for build_number in range(222, 231):
        task = next(
            task
            for task_id, task in tasks.items()
            if task_id.startswith(f"build-{build_number}-")
        )
        assert task["status"] == "superseded"

    current = tasks["issue-213-build-agent-queue-governance"]
    assert current["status"] == "open"
    assert current["github_issue_number"] == 213
