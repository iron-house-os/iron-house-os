from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ops.agent.iron_house_agent.config import AgentSettings, load_settings


def write_registry(root: Path, projects: list[dict] | None = None, **overrides: object) -> Path:
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "workspace": str(workspace),
        "state_directory": str(root / "state"),
        "worktrees_directory": str(root / "worktrees"),
        "max_parallel_jobs": 4,
        "dashboard": {"host": "127.0.0.1", "port": 8787},
        "production_requires_owner_approval": True,
        "projects": projects
        or [
            {
                "key": "test-project",
                "name": "Test Project",
                "repository": "iron-house-os/test-project",
                "directory": "test-project",
                "default_branch": "main",
                "staging_allowed_after_ci": True,
                "production_deploy_allowed": False,
            }
        ],
    }
    payload.update(overrides)
    path = root / "projects.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def git(*arguments: str, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def create_test_repository(settings: AgentSettings, project_key: str = "test-project") -> Path:
    project = settings.project(project_key)
    remote = settings.workspace.parent / "remote.git"
    checkout = settings.workspace / project.directory
    git("init", "--bare", str(remote), cwd=settings.workspace.parent)
    checkout.mkdir()
    git("init", cwd=checkout)
    git("config", "user.name", "Agent Test", cwd=checkout)
    git("config", "user.email", "agent-test@example.com", cwd=checkout)
    (checkout / "AGENTS.md").write_text(
        "# Test policy\n\nFeature branches only.\n", encoding="utf-8"
    )
    (checkout / "README.md").write_text("# Test repository\n", encoding="utf-8")
    git("add", "AGENTS.md", "README.md", cwd=checkout)
    git("commit", "-m", "Initial test repository", cwd=checkout)
    git("branch", "-M", "main", cwd=checkout)
    git("remote", "add", "origin", str(remote), cwd=checkout)
    git("push", "-u", "origin", "main", cwd=checkout)
    return checkout


@pytest.fixture
def settings(tmp_path: Path) -> AgentSettings:
    return load_settings(write_registry(tmp_path))
