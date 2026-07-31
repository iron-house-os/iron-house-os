from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .config import AgentSettings, Project


def _git(checkout: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return completed.stdout.strip()


def project_health(settings: AgentSettings, project: Project) -> dict[str, Any]:
    checkout = (settings.workspace / project.directory).resolve()
    base = {
        "key": project.key,
        "name": project.name,
        "repository": project.repository,
        "checkout": str(checkout),
        "production_deploy_allowed": False,
    }
    if checkout.parent != settings.workspace.resolve():
        return {**base, "status": "invalid", "detail": "Checkout escapes workspace"}
    if not (checkout / ".git").exists():
        return {**base, "status": "missing", "detail": "Repository checkout is missing"}
    if not (checkout / "AGENTS.md").is_file():
        return {**base, "status": "blocked", "detail": "AGENTS.md is missing"}
    try:
        branch = _git(checkout, "branch", "--show-current") or "detached"
        commit = _git(checkout, "rev-parse", "--short=12", "HEAD")
        status_lines = _git(checkout, "status", "--porcelain").splitlines()
        latest = _git(checkout, "log", "-1", "--pretty=%s")
    except (OSError, subprocess.SubprocessError) as error:
        return {**base, "status": "error", "detail": str(error)}
    status = "healthy" if not status_lines else "dirty"
    detail = "Clean checkout" if not status_lines else f"{len(status_lines)} uncommitted change(s)"
    return {
        **base,
        "status": status,
        "detail": detail,
        "branch": branch,
        "commit": commit,
        "latest_commit": latest,
    }


def repositories_health(settings: AgentSettings) -> list[dict[str, Any]]:
    return [project_health(settings, project) for project in settings.projects]
