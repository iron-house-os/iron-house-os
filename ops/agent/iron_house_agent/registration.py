from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import AgentSettings, Project, register_project
from .intake import READY_LABEL, ROLE_LABELS
from .runtime import AgentRuntime
from .store import JobStore, reject_embedded_secrets

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
_PRODUCTION_PATH_TOKEN = re.compile(
    r"(?:^|[-_.])(?:prod|production|live)(?:$|[-_.])", re.IGNORECASE
)
_GITHUB_HTTPS_REMOTE = re.compile(
    r"^https://github\.com/(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
    re.IGNORECASE,
)
_GITHUB_SSH_REMOTE = re.compile(
    r"^(?:git@github\.com:|ssh://git@github\.com/)(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
    re.IGNORECASE,
)
_SAFE_ENVIRONMENT_KEYS = {
    "HOME",
    "LANG",
    "LC_ALL",
    "LOGNAME",
    "PATH",
    "SHELL",
    "TERM",
    "TMPDIR",
    "USER",
    "XDG_CONFIG_HOME",
}


def _remote_repository(remote: str) -> str:
    for pattern in (_GITHUB_HTTPS_REMOTE, _GITHUB_SSH_REMOTE):
        match = pattern.fullmatch(remote.strip())
        if match:
            return match.group("repository")
    raise ValueError("Project checkout origin must be a GitHub repository")


class ProjectRegistrar:
    def __init__(
        self,
        settings: AgentSettings,
        store: JobStore,
        *,
        command_runner: CommandRunner = subprocess.run,
    ):
        self.settings = settings
        self.store = store
        self.command_runner = command_runner

    def register(self, project: Project, *, dry_run: bool = False) -> dict[str, Any]:
        self._validate_request(project)
        already_registered = self._validate_conflicts(project)
        repository = self._verify_github_repository(project)
        self._verify_remote_policy(project)
        destination = (self.settings.workspace / project.directory).resolve()

        if dry_run:
            return {
                "status": "planned",
                "project": project.key,
                "repository": repository,
                "checkout": str(destination),
                "labels": [READY_LABEL, *ROLE_LABELS],
                "already_registered": already_registered,
                "production_deploy_allowed": False,
                "mutations": False,
            }

        runtime = AgentRuntime(self.settings, self.store)
        checkout = runtime.clone_registered_project(project)
        self._verify_checkout_identity(project, checkout)
        self._ensure_labels(project)
        updated = register_project(self.settings.registry_path, project)
        self.store.initialize()
        self.store.update_intake_source(
            project.key,
            "ready",
            "Registration verified; awaiting the next scheduled GitHub issue poll",
        )
        return {
            "status": "already-registered" if already_registered else "registered",
            "project": project.key,
            "repository": repository,
            "checkout": str(checkout),
            "labels": [READY_LABEL, *ROLE_LABELS],
            "project_count": len(updated.projects),
            "intake_state": "ready",
            "production_deploy_allowed": False,
            "mutations": True,
        }

    def _validate_request(self, project: Project) -> None:
        project.validate()
        for value in (
            project.key,
            project.name,
            project.repository,
            project.directory,
            project.default_branch,
        ):
            reject_embedded_secrets(value)
        if _PRODUCTION_PATH_TOKEN.search(project.directory):
            raise ValueError("Production or live checkout paths cannot be registered")
        owner, _separator, _name = project.repository.partition("/")
        if owner.casefold() != "iron-house-os":
            raise ValueError("Only repositories in the trusted iron-house-os organization qualify")

    def _validate_conflicts(self, project: Project) -> bool:
        same_key = [item for item in self.settings.projects if item.key == project.key]
        if same_key:
            if same_key[0] == project:
                return True
            raise ValueError(f"Project key is already registered: {project.key}")
        if any(
            item.repository.casefold() == project.repository.casefold()
            for item in self.settings.projects
        ):
            raise ValueError(f"Repository is already registered: {project.repository}")
        if any(
            item.directory.casefold() == project.directory.casefold()
            for item in self.settings.projects
        ):
            raise ValueError(f"Directory is already registered: {project.directory}")
        return False

    def _verify_github_repository(self, project: Project) -> str:
        completed = self._run(
            [
                "gh",
                "repo",
                "view",
                project.repository,
                "--json",
                "nameWithOwner,defaultBranchRef",
            ]
        )
        payload = json.loads(completed.stdout)
        repository = str(payload.get("nameWithOwner", ""))
        if repository.casefold() != project.repository.casefold():
            raise ValueError("GitHub returned a different repository identity")
        default_branch = payload.get("defaultBranchRef") or {}
        if str(default_branch.get("name", "")) != project.default_branch:
            raise ValueError(
                f"Configured default branch does not match GitHub: {project.default_branch}"
            )
        return repository

    def _verify_remote_policy(self, project: Project) -> None:
        completed = self._run(
            [
                "gh",
                "api",
                "--method",
                "GET",
                f"repos/{project.repository}/contents/AGENTS.md",
                "-f",
                f"ref={project.default_branch}",
                "--jq",
                ".type",
            ]
        )
        if completed.stdout.strip() != "file":
            raise ValueError("Repository must contain AGENTS.md before enrollment")

    def _verify_checkout_identity(self, project: Project, checkout: Path) -> None:
        completed = self._run(["git", "-C", str(checkout), "remote", "get-url", "origin"])
        actual = _remote_repository(completed.stdout)
        if actual.casefold() != project.repository.casefold():
            raise ValueError(f"Checkout origin does not match registered repository: {actual}")
        if not (checkout / "AGENTS.md").is_file():
            raise ValueError("Project checkout is missing AGENTS.md")

    def _ensure_labels(self, project: Project) -> None:
        labels = {
            READY_LABEL: ("0E8A16", "Approved for autonomous agent intake"),
            **{
                label: ("1D76DB", f"Route to the {role} agent")
                for label, role in ROLE_LABELS.items()
            },
        }
        for label, (color, description) in labels.items():
            self._run(
                [
                    "gh",
                    "label",
                    "create",
                    label,
                    "--repo",
                    project.repository,
                    "--color",
                    color,
                    "--description",
                    description,
                    "--force",
                ]
            )

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.command_runner(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
                env=self._safe_environment(),
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"Registration command timed out: {command[0]}") from error
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"Registration command failed: {command[0]}") from error

    @staticmethod
    def _safe_environment() -> dict[str, str]:
        environment = {
            key: value for key, value in os.environ.items() if key in _SAFE_ENVIRONMENT_KEYS
        }
        environment.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        environment.setdefault("LANG", "C.UTF-8")
        return environment
