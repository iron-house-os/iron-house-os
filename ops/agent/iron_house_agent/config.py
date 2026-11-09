from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")
_DIRECTORY_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class Project:
    key: str
    name: str
    repository: str
    directory: str
    default_branch: str = "main"
    staging_allowed_after_ci: bool = True
    production_deploy_allowed: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Project:
        directory = str(value["directory"])
        key = str(value.get("key") or directory.lower().replace("_", "-"))
        project = cls(
            key=key,
            name=str(value["name"]),
            repository=str(value["repository"]),
            directory=directory,
            default_branch=str(value.get("default_branch", "main")),
            staging_allowed_after_ci=bool(value.get("staging_allowed_after_ci", True)),
            production_deploy_allowed=bool(value.get("production_deploy_allowed", False)),
        )
        project.validate()
        return project

    def validate(self) -> None:
        if not _KEY_RE.fullmatch(self.key):
            raise ValueError(f"Invalid project key: {self.key!r}")
        if not _REPOSITORY_RE.fullmatch(self.repository):
            raise ValueError(f"Invalid GitHub repository: {self.repository!r}")
        if not _DIRECTORY_RE.fullmatch(self.directory) or self.directory in {".", ".."}:
            raise ValueError(f"Invalid project directory: {self.directory!r}")
        if not _DIRECTORY_RE.fullmatch(self.default_branch):
            raise ValueError(f"Invalid default branch: {self.default_branch!r}")
        if self.production_deploy_allowed:
            raise ValueError("Autonomous production deployment must remain disabled")


@dataclass(frozen=True)
class AgentSettings:
    registry_path: Path
    workspace: Path
    state_directory: Path
    worktrees_directory: Path
    max_parallel_jobs: int
    dashboard_host: str
    dashboard_port: int
    projects: tuple[Project, ...]
    production_requires_owner_approval: bool = True

    def project(self, key_or_name: str) -> Project:
        needle = key_or_name.casefold()
        matches = [
            project
            for project in self.projects
            if needle
            in {project.key.casefold(), project.name.casefold(), project.directory.casefold()}
        ]
        if len(matches) != 1:
            raise ValueError(f"Unknown or ambiguous project: {key_or_name!r}")
        return matches[0]

    @property
    def database_path(self) -> Path:
        return self.state_directory / "jobs.sqlite3"


def _resolved_child(root: Path, child: str) -> Path:
    resolved_root = root.expanduser().resolve()
    resolved_child = (resolved_root / child).resolve()
    if resolved_child.parent != resolved_root:
        raise ValueError(f"Path escapes configured workspace: {child!r}")
    return resolved_child


def load_settings(registry_path: str | Path) -> AgentSettings:
    path = Path(registry_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    workspace = Path(payload["workspace"]).expanduser().resolve()
    state_directory = (
        Path(payload.get("state_directory", "/var/lib/iron-house-agent")).expanduser().resolve()
    )
    worktrees_directory = (
        Path(payload.get("worktrees_directory", workspace / "worktrees")).expanduser().resolve()
    )
    max_parallel_jobs = int(payload.get("max_parallel_jobs", 4))
    if not 1 <= max_parallel_jobs <= 16:
        raise ValueError("max_parallel_jobs must be between 1 and 16")
    dashboard = payload.get("dashboard", {})
    host = str(dashboard.get("host", "127.0.0.1"))
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("The agent dashboard must bind to loopback only")
    port = int(dashboard.get("port", 8787))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid dashboard port")
    if payload.get("production_requires_owner_approval") is not True:
        raise ValueError("production_requires_owner_approval must be true")
    projects = tuple(Project.from_dict(item) for item in payload.get("projects", []))
    if not projects:
        raise ValueError("At least one project must be registered")
    keys = [project.key for project in projects]
    repositories = [project.repository.casefold() for project in projects]
    directories = [project.directory.casefold() for project in projects]
    if len(keys) != len(set(keys)):
        raise ValueError("Project keys must be unique")
    if len(repositories) != len(set(repositories)):
        raise ValueError("Project repositories must be unique")
    if len(directories) != len(set(directories)):
        raise ValueError("Project directories must be unique")
    for project in projects:
        _resolved_child(workspace, project.directory)
    return AgentSettings(
        registry_path=path,
        workspace=workspace,
        state_directory=state_directory,
        worktrees_directory=worktrees_directory,
        max_parallel_jobs=max_parallel_jobs,
        dashboard_host=host,
        dashboard_port=port,
        projects=projects,
    )


def register_project(registry_path: str | Path, project: Project) -> AgentSettings:
    project.validate()
    settings = load_settings(registry_path)
    if any(existing.key == project.key for existing in settings.projects):
        existing = settings.project(project.key)
        if existing == project:
            return settings
        raise ValueError(f"Project key is already registered: {project.key}")
    if any(
        existing.repository.casefold() == project.repository.casefold()
        for existing in settings.projects
    ):
        raise ValueError(f"Repository is already registered: {project.repository}")
    if any(
        existing.directory.casefold() == project.directory.casefold()
        for existing in settings.projects
    ):
        raise ValueError(f"Directory is already registered: {project.directory}")
    _resolved_child(settings.workspace, project.directory)

    payload = json.loads(settings.registry_path.read_text(encoding="utf-8"))
    payload.setdefault("projects", []).append(asdict(project))
    settings.registry_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{settings.registry_path.name}.", dir=settings.registry_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, settings.registry_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return load_settings(settings.registry_path)
