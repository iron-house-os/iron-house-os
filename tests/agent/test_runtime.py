from __future__ import annotations

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ops.agent.iron_house_agent.runtime import AgentRuntime, WorkerPool
from ops.agent.iron_house_agent.store import JobStore
from tests.agent.conftest import create_test_repository


def test_job_runs_in_issue_linked_isolated_worktree(settings) -> None:
    create_test_repository(settings)
    store = JobStore(settings.database_path)
    runtime = AgentRuntime(settings, store)
    runtime.initialize()
    queued = store.enqueue(
        project_key="test-project",
        role="build",
        issue_number=107,
        title="Exercise isolated worktree",
        prompt="Inspect the test repository.",
    )
    observed: dict[str, object] = {}

    def executor(job: dict, worktree: Path, branch: str, log_path: Path) -> int:
        observed.update(job=job, worktree=worktree, branch=branch)
        log_path.write_text('{"type":"turn.completed"}\n', encoding="utf-8")
        return 0

    completed = runtime.run_once("test-worker", executor=executor)

    assert completed is not None
    assert completed["id"] == queued["id"]
    assert completed["status"] == "succeeded"
    assert str(observed["branch"]).startswith("agent/build/107-job-")
    worktree = Path(observed["worktree"])
    current_branch = subprocess.run(
        ["git", "-C", str(worktree), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert current_branch == observed["branch"]
    assert worktree.parent.parent == settings.worktrees_directory


def test_worker_pool_enforces_configured_concurrency_limit(settings) -> None:
    store = JobStore(settings.database_path)
    runtime = AgentRuntime(settings, store)

    with pytest.raises(ValueError, match="between 1 and 4"):
        WorkerPool(runtime, 5)


def test_two_jobs_execute_concurrently_in_distinct_worktrees(settings) -> None:
    create_test_repository(settings)
    store = JobStore(settings.database_path)
    runtime = AgentRuntime(settings, store)
    runtime.initialize()
    for number in (108, 109):
        store.enqueue(
            project_key="test-project",
            role="build",
            issue_number=number,
            title=f"Concurrent job {number}",
            prompt="Exercise safe parallel execution.",
        )
    barrier = threading.Barrier(2)
    state_lock = threading.Lock()
    active = 0
    max_active = 0
    worktrees: set[Path] = set()

    def executor(job: dict, worktree: Path, branch: str, log_path: Path) -> int:
        nonlocal active, max_active
        with state_lock:
            active += 1
            max_active = max(max_active, active)
            worktrees.add(worktree)
        barrier.wait(timeout=5)
        time.sleep(0.05)
        log_path.write_text('{"type":"turn.completed"}\n', encoding="utf-8")
        with state_lock:
            active -= 1
        return 0

    with ThreadPoolExecutor(max_workers=2) as pool:
        completed = list(
            pool.map(
                lambda worker: runtime.run_once(worker, executor=executor),
                ("worker-1", "worker-2"),
            )
        )

    assert max_active == 2
    assert len(worktrees) == 2
    assert {job["status"] for job in completed if job is not None} == {"succeeded"}


def test_smoke_prompt_forbids_writes_and_production(settings) -> None:
    store = JobStore(settings.database_path)
    runtime = AgentRuntime(settings, store)
    runtime.initialize()
    job = runtime.enqueue_smoke_test("test-project", 107)

    prompt = runtime._agent_prompt(job, "agent/build/107-job-deadbeef")

    assert "read-only smoke test" in prompt
    assert "Do not modify files" in prompt
    assert "Never deploy or modify production" in prompt


def test_codex_command_is_noninteractive_and_disables_smoke_network() -> None:
    smoke = AgentRuntime._codex_command("smoke", network_access=False)
    standard = AgentRuntime._codex_command("standard", network_access=True)

    assert 'approval_policy="never"' in smoke
    assert "--ask-for-approval" not in smoke
    assert "sandbox_workspace_write.network_access=false" in smoke
    assert "sandbox_workspace_write.network_access=true" in standard


def test_zero_exit_blocked_agent_message_fails_managed_job(settings, monkeypatch) -> None:
    create_test_repository(settings)
    store = JobStore(settings.database_path)
    runtime = AgentRuntime(settings, store)
    runtime.initialize()
    store.enqueue(
        project_key="test-project",
        role="build",
        issue_number=112,
        title="Blocked autonomous build",
        prompt="Build the approved feature.",
    )
    monkeypatch.setattr(runtime, "preflight", dict)

    def blocked_executor(job: dict, worktree: Path, branch: str, log_path: Path) -> int:
        log_path.write_text(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": "Blocked by the execution sandbox before repository access.",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(runtime, "_execute_codex", blocked_executor)

    completed = runtime.run_once("managed-worker")

    assert completed is not None
    assert completed["status"] == "failed"
    assert completed["exit_code"] == 2
    assert "reported the task blocked" in completed["result_summary"]


def test_build_outcome_rejects_no_commit(settings) -> None:
    create_test_repository(settings)
    store = JobStore(settings.database_path)
    runtime = AgentRuntime(settings, store)
    runtime.initialize()
    job = store.enqueue(
        project_key="test-project",
        role="build",
        issue_number=112,
        title="No-op build",
        prompt="Build the approved feature.",
    )
    branch, worktree = runtime.prepare_worktree(settings.project("test-project"), job)
    log_path = settings.state_directory / "logs" / "noop.jsonl"
    log_path.write_text('{"type":"turn.completed"}\n', encoding="utf-8")

    error = runtime._validate_codex_outcome(
        settings.project("test-project"), job, worktree, branch, log_path
    )

    assert error == "Codex did not create a new commit"


def test_build_outcome_accepts_pushed_branch_and_draft_pr(settings, monkeypatch) -> None:
    create_test_repository(settings)
    store = JobStore(settings.database_path)
    runtime = AgentRuntime(settings, store)
    runtime.initialize()
    job = store.enqueue(
        project_key="test-project",
        role="build",
        issue_number=112,
        title="Published build",
        prompt="Build the approved feature.",
    )
    project = settings.project("test-project")
    branch, worktree = runtime.prepare_worktree(project, job)
    (worktree / "FEATURE.md").write_text("# Feature\n", encoding="utf-8")
    subprocess.run(["git", "add", "FEATURE.md"], cwd=worktree, check=True)
    subprocess.run(["git", "commit", "-m", "Add feature"], cwd=worktree, check=True)
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=worktree, check=True)
    log_path = settings.state_directory / "logs" / "published.jsonl"
    log_path.write_text('{"type":"turn.completed"}\n', encoding="utf-8")
    original_run = subprocess.run

    def command_runner(command, **kwargs):
        if command[:3] == ["gh", "pr", "view"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "isDraft": True,
                        "state": "OPEN",
                        "headRefName": branch,
                        "baseRefName": "main",
                        "url": "https://github.com/iron-house-os/test-project/pull/1",
                    }
                ),
                stderr="",
            )
        return original_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", command_runner)

    error = runtime._validate_codex_outcome(project, job, worktree, branch, log_path)

    assert error is None
