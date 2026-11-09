from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ops.agent.iron_house_agent.store import JobStore


def _enqueue(store: JobStore, number: int) -> dict:
    return store.enqueue(
        project_key="test-project",
        role="build",
        issue_number=100 + number,
        title=f"Test job {number}",
        prompt=f"Perform bounded test task {number}.",
    )


def test_concurrent_workers_claim_distinct_jobs(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.initialize()
    queued = [_enqueue(store, number) for number in range(4)]

    with ThreadPoolExecutor(max_workers=4) as executor:
        claimed = list(executor.map(store.claim_next, [f"worker-{number}" for number in range(4)]))

    claimed_ids = {job["id"] for job in claimed if job is not None}
    assert claimed_ids == {job["id"] for job in queued}
    assert len(claimed_ids) == 4


def test_snapshot_hides_task_prompt(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.initialize()
    _enqueue(store, 1)

    snapshot = store.snapshot()

    assert "prompt" not in snapshot["queue"][0]


def test_enqueue_rejects_secret_like_text(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.initialize()

    with pytest.raises(ValueError, match="secret"):
        store.enqueue(
            project_key="test-project",
            role="build",
            issue_number=101,
            title="Unsafe task",
            prompt="Use OPENAI_API_KEY=secret-value to run this task.",
        )
