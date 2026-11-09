from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ops.agent.iron_house_agent.config import Project, load_settings
from ops.agent.iron_house_agent.registration import ProjectRegistrar
from ops.agent.iron_house_agent.store import JobStore


class GitHubRunner:
    def __init__(self, project: Project, *, policy_type: str = "file"):
        self.project = project
        self.policy_type = policy_type
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, kwargs))
        if command[:3] == ["gh", "repo", "view"]:
            stdout = json.dumps(
                {
                    "nameWithOwner": self.project.repository,
                    "defaultBranchRef": {"name": self.project.default_branch},
                }
            )
        elif command[:2] == ["gh", "api"]:
            stdout = f"{self.policy_type}\n"
        elif command[:4] == ["git", "-C", command[2], "remote"]:
            stdout = f"https://github.com/{self.project.repository}.git\n"
        else:
            stdout = ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


def future_project(directory: str = "future-project") -> Project:
    return Project(
        key="future-project",
        name="Future Project",
        repository="iron-house-os/future-project",
        directory=directory,
    )


def create_existing_checkout(workspace: Path, project: Project) -> Path:
    checkout = workspace / project.directory
    checkout.mkdir()
    subprocess.run(["git", "init"], cwd=checkout, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", f"https://github.com/{project.repository}.git"],
        cwd=checkout,
        check=True,
    )
    (checkout / "AGENTS.md").write_text("# Project policy\n", encoding="utf-8")
    return checkout


def test_dry_run_validates_without_mutating_registry_or_state(settings) -> None:
    project = future_project()
    runner = GitHubRunner(project)
    original_registry = settings.registry_path.read_bytes()
    registrar = ProjectRegistrar(settings, JobStore(settings.database_path), command_runner=runner)

    result = registrar.register(project, dry_run=True)

    assert result["status"] == "planned"
    assert result["mutations"] is False
    assert result["production_deploy_allowed"] is False
    assert settings.registry_path.read_bytes() == original_registry
    assert not settings.database_path.exists()
    assert not (settings.workspace / project.directory).exists()
    assert not any(call[0][:3] == ["gh", "label", "create"] for call in runner.calls)


def test_registration_is_atomic_idempotent_and_creates_standard_labels(settings) -> None:
    project = future_project()
    create_existing_checkout(settings.workspace, project)
    runner = GitHubRunner(project)
    store = JobStore(settings.database_path)

    first = ProjectRegistrar(settings, store, command_runner=runner).register(project)
    updated = load_settings(settings.registry_path)
    second_runner = GitHubRunner(project)
    second = ProjectRegistrar(updated, store, command_runner=second_runner).register(project)
    snapshot = store.snapshot()

    assert first["status"] == "registered"
    assert second["status"] == "already-registered"
    assert len(updated.projects) == 2
    assert len(load_settings(settings.registry_path).projects) == 2
    label_calls = [call for call, _kwargs in runner.calls if call[:3] == ["gh", "label", "create"]]
    assert len(label_calls) == 9
    assert {call[3] for call in label_calls} == set(first["labels"])
    assert snapshot["intake_sources"][0]["project_key"] == project.key
    assert snapshot["intake_sources"][0]["state"] == "ready"


def test_registration_rejects_production_path_before_external_commands(settings) -> None:
    project = future_project("future-production")
    runner = GitHubRunner(project)

    with pytest.raises(ValueError, match="Production or live"):
        ProjectRegistrar(
            settings, JobStore(settings.database_path), command_runner=runner
        ).register(project, dry_run=True)

    assert runner.calls == []


def test_registration_rejects_repository_outside_trusted_organization(settings) -> None:
    project = Project(
        key="external-project",
        name="External Project",
        repository="outside-owner/external-project",
        directory="external-project",
    )
    runner = GitHubRunner(project)

    with pytest.raises(ValueError, match="trusted iron-house-os"):
        ProjectRegistrar(
            settings, JobStore(settings.database_path), command_runner=runner
        ).register(project, dry_run=True)

    assert runner.calls == []


def test_registration_rejects_missing_remote_policy(settings) -> None:
    project = future_project()
    runner = GitHubRunner(project, policy_type="directory")

    with pytest.raises(ValueError, match="AGENTS.md"):
        ProjectRegistrar(
            settings, JobStore(settings.database_path), command_runner=runner
        ).register(project, dry_run=True)

    assert not (settings.workspace / project.directory).exists()


def test_registration_uses_saved_auth_without_inheriting_token(monkeypatch, settings) -> None:
    project = future_project()
    runner = GitHubRunner(project)
    monkeypatch.setenv("GH_TOKEN", "must-not-be-inherited")

    ProjectRegistrar(settings, JobStore(settings.database_path), command_runner=runner).register(
        project, dry_run=True
    )

    assert runner.calls
    assert all("GH_TOKEN" not in kwargs["env"] for _command, kwargs in runner.calls)


def test_github_failure_returns_redacted_operational_error(settings) -> None:
    project = future_project()

    def failed_runner(command: list[str], **kwargs):
        raise subprocess.CalledProcessError(
            1,
            command,
            stderr="authentication failed with GH_TOKEN=must-not-leak",
        )

    with pytest.raises(RuntimeError, match="Registration command failed: gh") as error:
        ProjectRegistrar(
            settings,
            JobStore(settings.database_path),
            command_runner=failed_runner,
        ).register(project, dry_run=True)

    assert "must-not-leak" not in str(error.value)
