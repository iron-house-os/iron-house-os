from __future__ import annotations

import subprocess

from ops.agent.iron_house_agent.intake import GitHubIssueIntake
from ops.agent.iron_house_agent.store import JobStore
from tests.agent.conftest import create_test_repository


def issue(
    *,
    labels: list[str],
    body: str = "Update the approved documentation and open a draft pull request.",
    updated_at: str = "2026-07-31T12:00:00Z",
) -> dict:
    return {
        "number": 109,
        "title": "Document the GitHub issue intake workflow",
        "body": body,
        "updatedAt": updated_at,
        "labels": [{"name": label} for label in labels],
    }


def test_explicitly_labelled_issue_is_enqueued_once(settings) -> None:
    create_test_repository(settings)
    store = JobStore(settings.database_path)
    store.initialize()
    payload = issue(labels=["agent:ready", "agent:documentation"])
    intake = GitHubIssueIntake(settings, store, source=lambda project: [payload])

    first = intake.poll_once()
    second = intake.poll_once()
    snapshot = store.snapshot()

    assert first == {"accepted": 1, "blocked": 0, "duplicates": 0, "sources_blocked": 0}
    assert second == {"accepted": 0, "blocked": 0, "duplicates": 1, "sources_blocked": 0}
    assert len(snapshot["queue"]) == 1
    assert snapshot["queue"][0]["role"] == "documentation"
    assert snapshot["intake_history"][0]["status"] == "accepted"
    assert "prompt" not in snapshot["intake_history"][0]


def test_ambiguous_or_unsupported_role_labels_are_blocked(settings) -> None:
    create_test_repository(settings)
    store = JobStore(settings.database_path)
    store.initialize()
    ambiguous = issue(labels=["agent:ready", "agent:build", "agent:documentation"])
    unsupported = {
        **issue(
            labels=["agent:ready", "agent:unknown"],
            updated_at="2026-07-31T12:01:00Z",
        ),
        "number": 110,
    }
    intake = GitHubIssueIntake(settings, store, source=lambda project: [ambiguous, unsupported])

    summary = intake.poll_once()
    snapshot = store.snapshot()

    assert summary["blocked"] == 2
    assert snapshot["queue"] == []
    assert all("exactly one" in item["detail"] for item in snapshot["intake_history"])


def test_secret_and_production_requests_are_blocked(settings) -> None:
    create_test_repository(settings)
    store = JobStore(settings.database_path)
    store.initialize()
    candidates = [
        issue(
            labels=["agent:ready", "agent:build"],
            body="Use OPENAI_API_KEY=secret-value to complete this task.",
        ),
        {
            **issue(
                labels=["agent:ready", "agent:build"],
                body="Deploy these changes to production now.",
                updated_at="2026-07-31T12:01:00Z",
            ),
            "number": 110,
        },
    ]
    intake = GitHubIssueIntake(settings, store, source=lambda project: candidates)

    summary = intake.poll_once()
    snapshot = store.snapshot()

    assert summary["blocked"] == 2
    assert snapshot["queue"] == []
    assert {item["status"] for item in snapshot["intake_history"]} == {"blocked"}
    assert any("secret" in item["detail"] for item in snapshot["intake_history"])
    assert any("production" in item["detail"] for item in snapshot["intake_history"])


def test_github_failure_blocks_source_without_enqueuing(settings) -> None:
    store = JobStore(settings.database_path)
    store.initialize()

    def unavailable(project):
        raise RuntimeError("GitHub authentication unavailable")

    summary = GitHubIssueIntake(settings, store, source=unavailable).poll_once()
    snapshot = store.snapshot()

    assert summary["sources_blocked"] == 1
    assert snapshot["queue"] == []
    assert snapshot["intake_sources"][0]["state"] == "blocked"
    assert "authentication unavailable" in snapshot["intake_sources"][0]["detail"]


def test_github_source_uses_exact_ready_label_and_saved_auth(monkeypatch, settings) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, stdout="[]", stderr="")

    monkeypatch.setenv("GH_TOKEN", "must-not-be-inherited")
    monkeypatch.setattr(subprocess, "run", fake_run)
    store = JobStore(settings.database_path)
    store.initialize()
    intake = GitHubIssueIntake(settings, store)

    assert intake._list_issues(settings.project("test-project")) == []
    assert observed["command"][0:3] == ["gh", "issue", "list"]
    label_index = observed["command"].index("--label")
    assert observed["command"][label_index + 1] == "agent:ready"
    assert "GH_TOKEN" not in observed["environment"]
