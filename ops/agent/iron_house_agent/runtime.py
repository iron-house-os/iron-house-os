from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_UN, flock
from pathlib import Path
from typing import Any

from .config import AgentSettings, Project
from .store import AGENT_ROLES, JobStore

Executor = Callable[[dict[str, Any], Path, str, Path], int]
_BRANCH_NAMESPACES = {
    "build": "build",
    "ci-repair": "ci",
    "code-review": "review",
    "qa-browser": "qa",
    "security-audit": "security",
    "dependency-update": "deps",
    "documentation": "docs",
    "issue-planning": "planning",
}
_ROLE_WORKFLOWS = {
    "build": (
        "Implement only the approved scope, run the relevant checks, record exact evidence, commit "
        "the result, push this feature branch, and open a draft pull request linked to the issue."
    ),
    "ci-repair": (
        "Reproduce the failing check, apply the narrowest safe repair, rerun the check, record exact "
        "evidence, commit the result, push this feature branch, and open a draft pull request."
    ),
    "code-review": (
        "Inspect the requested pull request and its checks for defects, regressions, missing tests, "
        "and policy violations. Do not modify code. Submit review comments only when the task "
        "explicitly requests it."
    ),
    "qa-browser": (
        "Test only a local or explicitly identified staging environment. Record repeatable results, "
        "screenshots, traces, and console evidence where applicable. Do not change application code "
        "unless the approved task explicitly requests a test repair."
    ),
    "security-audit": (
        "Audit the approved scope without exposing secrets. Record reproducible findings. If the task "
        "authorizes a repair, make the smallest safe change, test it, and open a draft pull request."
    ),
    "dependency-update": (
        "Update only the approved dependency set, preserve lockfiles, run relevant checks, record exact "
        "evidence, commit the result, push this feature branch, and open a draft pull request."
    ),
    "documentation": (
        "Update only the approved documentation, verify commands and links where practical, commit the "
        "result, push this feature branch, and open a draft pull request."
    ),
    "issue-planning": (
        "Convert only the approved plan or findings into prioritized GitHub issues with acceptance "
        "criteria, risks, dependencies, and approval gates. Do not implement or merge the issues."
    ),
}
_PUBLISH_REQUIRED_ROLES = {
    "build",
    "ci-repair",
    "dependency-update",
    "documentation",
}
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
    "XDG_DATA_HOME",
    "XDG_RUNTIME_DIR",
    "CODEX_HOME",
}


class AgentRuntime:
    def __init__(self, settings: AgentSettings, store: JobStore):
        self.settings = settings
        self.store = store

    def initialize(self) -> None:
        self.settings.state_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.settings.worktrees_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.settings.state_directory / "logs").mkdir(parents=True, exist_ok=True, mode=0o700)
        self.store.initialize()

    def preflight(self) -> dict[str, str]:
        checks = {
            "codex": ["codex", "--version"],
            "codex_auth": ["codex", "login", "status"],
            "git": ["git", "--version"],
            "github_auth": ["gh", "auth", "status"],
            "codex_sandbox": [
                "bwrap",
                "--unshare-user",
                "--uid",
                "0",
                "--gid",
                "0",
                "--ro-bind",
                "/",
                "/",
                "--tmpfs",
                "/tmp",
                "/usr/bin/python3",
                "-c",
                (
                    "import os; "
                    "fd = os.open('/tmp', os.O_TMPFILE | os.O_RDWR, 0o600); "
                    "os.write(fd, b'codex-sandbox-probe'); os.close(fd)"
                ),
            ],
        }
        results: dict[str, str] = {}
        for name, command in checks.items():
            try:
                completed = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    env=self._safe_environment(),
                )
            except FileNotFoundError as error:
                raise RuntimeError(f"Required command is missing: {command[0]}") from error
            except subprocess.CalledProcessError as error:
                detail = (error.stdout or error.stderr or "authentication failed").strip()
                if name == "codex_sandbox":
                    raise RuntimeError(
                        "codex_sandbox preflight failed: Bubblewrap cannot create its user "
                        f"namespace ({detail}). Re-run the agent installer as root."
                    ) from error
                raise RuntimeError(f"{name} preflight failed: {detail}") from error
            output = (completed.stdout or completed.stderr).strip().splitlines()
            results[name] = output[0] if output else "ok"
        return results

    def enqueue_smoke_test(self, project_key: str, issue_number: int) -> dict[str, Any]:
        project = self.settings.project(project_key)
        return self.store.enqueue(
            project_key=project.key,
            role="build",
            issue_number=issue_number,
            title=f"Non-destructive Codex smoke test for {project.name}",
            prompt=(
                "Inspect the repository policy and current Git branch, then report the repository name, "
                "current branch, and the first three top-level paths. Do not modify files, install "
                "dependencies, commit, push, open a pull request, contact production, or access secrets."
            ),
            mode="smoke",
        )

    def run_once(self, worker_id: str, executor: Executor | None = None) -> dict[str, Any] | None:
        managed_execution = executor is None
        if managed_execution:
            self.preflight()
        job = self.store.claim_next(worker_id)
        if job is None:
            return None
        try:
            project = self.settings.project(job["project_key"])
            branch, worktree = self.prepare_worktree(project, job)
            log_path = self.settings.state_directory / "logs" / f"{job['id']}.jsonl"
            log_path.touch(mode=0o600, exist_ok=False)
            self.store.set_execution_metadata(
                job["id"], branch=branch, worktree=str(worktree), log_path=str(log_path)
            )
            run = executor or self._execute_codex
            exit_code = run(job, worktree, branch, log_path)
            validation_error = None
            if exit_code == 0 and managed_execution:
                validation_error = self._validate_codex_outcome(
                    project, job, worktree, branch, log_path
                )
            if validation_error:
                self.store.fail(job["id"], validation_error, exit_code=2)
            else:
                summary = (
                    "Codex task completed"
                    if exit_code == 0
                    else "Codex task failed; inspect the job log"
                )
                self.store.finish(job["id"], exit_code=exit_code, summary=summary)
        except Exception as error:  # noqa: BLE001 - a worker records task failures instead of dying
            self.store.fail(job["id"], f"{type(error).__name__}: {error}")
        return self.store.get_job(job["id"])

    def _validate_codex_outcome(
        self,
        project: Project,
        job: dict[str, Any],
        worktree: Path,
        branch: str,
        log_path: Path,
    ) -> str | None:
        message = self._last_agent_message(log_path)
        normalized = message.strip().casefold()
        if normalized.startswith(("blocked", "i am blocked", "i'm blocked")):
            return "Codex reported the task blocked; inspect the job log"
        if job["mode"] == "smoke" or job["role"] not in _PUBLISH_REQUIRED_ROLES:
            return None

        if self._git_output(worktree, "status", "--porcelain"):
            return "Codex left uncommitted changes; inspect the job worktree"
        head = self._git_output(worktree, "rev-parse", "HEAD")
        base = self._git_output(worktree, "rev-parse", f"origin/{project.default_branch}")
        if head == base:
            return "Codex did not create a new commit"
        try:
            remote_ref = self._git_output(
                worktree,
                "ls-remote",
                "--exit-code",
                "origin",
                f"refs/heads/{branch}",
            )
        except subprocess.CalledProcessError:
            return "Codex did not push the issue-linked feature branch"
        remote_head = remote_ref.partition("\t")[0]
        if remote_head != head:
            return "Codex pushed branch does not contain the completed local commit"

        try:
            completed = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    branch,
                    "--repo",
                    project.repository,
                    "--json",
                    "isDraft,state,headRefName,baseRefName,url",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=self._safe_environment(),
            )
            pull_request = json.loads(completed.stdout)
        except (OSError, subprocess.SubprocessError, ValueError):
            return "Codex did not open a verifiable draft pull request"
        if (
            pull_request.get("state") != "OPEN"
            or pull_request.get("isDraft") is not True
            or pull_request.get("headRefName") != branch
            or pull_request.get("baseRefName") != project.default_branch
        ):
            return "Codex pull request does not match the required open draft workflow"
        return None

    @staticmethod
    def _last_agent_message(log_path: Path) -> str:
        last_message = ""
        with log_path.open(encoding="utf-8") as log:
            for line in log:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                item = event.get("item") or {}
                if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                    last_message = str(item.get("text") or "")
        return last_message

    def prepare_worktree(self, project: Project, job: dict[str, Any]) -> tuple[str, Path]:
        checkout = (self.settings.workspace / project.directory).resolve()
        if checkout.parent != self.settings.workspace.resolve():
            raise RuntimeError("Project checkout escapes the configured workspace")
        if not (checkout / ".git").exists():
            raise RuntimeError(f"Project checkout is missing: {checkout}")
        if not (checkout / "AGENTS.md").is_file():
            raise RuntimeError(f"Project is not enrolled; AGENTS.md is missing: {project.key}")

        namespace = _BRANCH_NAMESPACES[job["role"]]
        suffix = re.sub(r"[^a-f0-9]", "", job["id"].lower())[:8]
        branch = f"agent/{namespace}/{job['issue_number']}-job-{suffix}"
        project_worktrees = (self.settings.worktrees_directory / project.key).resolve()
        if project_worktrees.parent != self.settings.worktrees_directory.resolve():
            raise RuntimeError("Project worktree directory escapes the configured root")
        project_worktrees.mkdir(parents=True, exist_ok=True, mode=0o700)
        worktree = (project_worktrees / job["id"]).resolve()
        if worktree.parent != project_worktrees:
            raise RuntimeError("Job worktree escapes the project worktree directory")
        if worktree.exists():
            raise RuntimeError(f"Job worktree already exists: {worktree}")

        with self._project_lock(project.key):
            self._git(checkout, "fetch", "origin", "--prune")
            self._git(
                checkout,
                "worktree",
                "add",
                "-b",
                branch,
                str(worktree),
                f"origin/{project.default_branch}",
            )
        return branch, worktree

    def clone_registered_project(self, project: Project) -> Path:
        destination = (self.settings.workspace / project.directory).resolve()
        if destination.parent != self.settings.workspace.resolve():
            raise RuntimeError("Project destination escapes the workspace")
        if (destination / ".git").exists():
            if not (destination / "AGENTS.md").is_file():
                raise RuntimeError("Existing checkout is missing AGENTS.md")
            return destination
        if destination.exists():
            raise RuntimeError(f"Project destination already exists: {destination}")
        temporary = destination.with_name(f".{destination.name}.registering")
        if temporary.exists():
            raise RuntimeError(f"Registration staging directory already exists: {temporary}")
        try:
            subprocess.run(
                [
                    "gh",
                    "repo",
                    "clone",
                    project.repository,
                    str(temporary),
                    "--",
                    "--branch",
                    project.default_branch,
                    "--single-branch",
                ],
                check=True,
                timeout=300,
                env=self._safe_environment(),
            )
            if not (temporary / "AGENTS.md").is_file():
                raise RuntimeError("Repository must contain AGENTS.md before enrollment")
            temporary.rename(destination)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            if temporary.exists() and temporary.parent == self.settings.workspace.resolve():
                shutil.rmtree(temporary)
            raise RuntimeError("GitHub repository clone failed") from error
        except Exception:
            if temporary.exists() and temporary.parent == self.settings.workspace.resolve():
                shutil.rmtree(temporary)
            raise
        return destination

    def _execute_codex(
        self, job: dict[str, Any], worktree: Path, branch: str, log_path: Path
    ) -> int:
        prompt = self._agent_prompt(job, branch)
        command = self._codex_command(prompt, network_access=job["mode"] != "smoke")
        with log_path.open("a", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                cwd=worktree,
                env=self._safe_environment(),
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return process.wait()

    @staticmethod
    def _codex_command(prompt: str, *, network_access: bool) -> list[str]:
        return [
            "codex",
            "exec",
            "--ephemeral",
            "--json",
            "--sandbox",
            "workspace-write",
            "--config",
            'approval_policy="never"',
            "--config",
            f"sandbox_workspace_write.network_access={str(network_access).lower()}",
            prompt,
        ]

    @staticmethod
    def _agent_prompt(job: dict[str, Any], branch: str) -> str:
        gates = (
            "Read and follow AGENTS.md before acting. Work only in the current isolated worktree on "
            f"branch {branch}. Never deploy or modify production, reveal or move secrets, weaken tests "
            "or approval gates, activate payments or invitations, merge your own pull request, or claim "
            "a check passed without executing it. If any task instruction conflicts with these gates, "
            "do not execute the conflicting part; report it as blocked."
        )
        if job["mode"] == "smoke":
            workflow = (
                "This is a read-only smoke test. Do not modify files, commit, push, open a pull request, "
                "install dependencies, or make any external change."
            )
        else:
            workflow = (
                f"Work as the {job['role']} agent for GitHub issue #{job['issue_number']}. "
                f"{_ROLE_WORKFLOWS[job['role']]} Do not approve or merge your own work."
            )
        return f"{gates}\n\n{workflow}\n\nTask: {job['title']}\n\n{job['prompt']}"

    @staticmethod
    def _git(checkout: Path, *arguments: str) -> None:
        AgentRuntime._git_output(checkout, *arguments)

    @staticmethod
    def _git_output(checkout: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(checkout), *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
            env=AgentRuntime._safe_environment(),
        )
        return completed.stdout.strip()

    @contextmanager
    def _project_lock(self, project_key: str):
        locks_directory = self.settings.state_directory / "locks"
        locks_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = locks_directory / f"{project_key}.lock"
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            os.chmod(lock_path, 0o600)
            flock(lock_file.fileno(), LOCK_EX)
            try:
                yield
            finally:
                flock(lock_file.fileno(), LOCK_UN)

    @staticmethod
    def _safe_environment() -> dict[str, str]:
        environment = {
            key: value for key, value in os.environ.items() if key in _SAFE_ENVIRONMENT_KEYS
        }
        environment.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        environment.setdefault("LANG", "C.UTF-8")
        return environment


class WorkerPool:
    def __init__(self, runtime: AgentRuntime, workers: int):
        if not 1 <= workers <= runtime.settings.max_parallel_jobs:
            raise ValueError(f"workers must be between 1 and {runtime.settings.max_parallel_jobs}")
        self.runtime = runtime
        self.workers = workers
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []

    def start(self) -> None:
        for number in range(1, self.workers + 1):
            worker_id = f"worker-{number}"
            thread = threading.Thread(
                target=self._worker_loop, args=(worker_id,), name=worker_id, daemon=True
            )
            thread.start()
            self.threads.append(thread)

    def wait(self) -> None:
        try:
            while any(thread.is_alive() for thread in self.threads):
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=5)

    def _worker_loop(self, worker_id: str) -> None:
        while not self.stop_event.is_set():
            try:
                job = self.runtime.run_once(worker_id)
            except RuntimeError:
                self.runtime.store.heartbeat(worker_id, "blocked", None)
                self.stop_event.wait(10)
                continue
            if job is None:
                self.stop_event.wait(2)


def supported_roles() -> tuple[str, ...]:
    return AGENT_ROLES
