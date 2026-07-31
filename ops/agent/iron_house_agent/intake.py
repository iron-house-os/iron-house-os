from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from collections.abc import Callable
from typing import Any

from .config import AgentSettings, Project
from .store import AGENT_ROLES, JobStore, reject_embedded_secrets

IssueSource = Callable[[Project], list[dict[str, Any]]]
READY_LABEL = "agent:ready"
ROLE_LABELS = {f"agent:{role}": role for role in AGENT_ROLES}
_UNSAFE_ACTION_PATTERNS = (
    re.compile(
        r"\b(?:deploy|release|push)\b.{0,60}\b(?:to|into|on)\s+(?:live|production)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:modify|delete|reset|migrate|rotate)\b.{0,60}\b(?:production|live)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:bypass|disable|remove|weaken)\b.{0,60}\b(?:approval|payment|owner|launch|production|safety)\s+gate\b",
        re.IGNORECASE,
    ),
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


def reject_unsafe_issue_text(value: str) -> None:
    reject_embedded_secrets(value)
    if any(pattern.search(value) for pattern in _UNSAFE_ACTION_PATTERNS):
        raise ValueError("Issue requests a prohibited production or approval-gate action")


def safe_error_detail(error: Exception) -> str:
    detail = f"{type(error).__name__}: {error}"
    try:
        reject_embedded_secrets(detail)
    except ValueError:
        return "GitHub intake failed; sensitive detail redacted"
    return detail


class GitHubIssueIntake:
    def __init__(
        self,
        settings: AgentSettings,
        store: JobStore,
        source: IssueSource | None = None,
    ):
        self.settings = settings
        self.store = store
        self.source = source or self._list_issues

    def poll_once(self) -> dict[str, Any]:
        summary = {"accepted": 0, "blocked": 0, "duplicates": 0, "sources_blocked": 0}
        for project in self.settings.projects:
            try:
                issues = self.source(project)
                for issue in issues:
                    result = self._process_issue(project, issue)
                    if result["duplicate"]:
                        summary["duplicates"] += 1
                    elif result["status"] == "accepted":
                        summary["accepted"] += 1
                    else:
                        summary["blocked"] += 1
                self.store.update_intake_source(
                    project.key, "ready", f"Checked {len(issues)} explicitly labelled issue(s)"
                )
            except Exception as error:  # noqa: BLE001 - fail one repository closed, keep polling others
                summary["sources_blocked"] += 1
                self.store.update_intake_source(project.key, "blocked", safe_error_detail(error))
        return summary

    def _process_issue(self, project: Project, issue: dict[str, Any]) -> dict[str, Any]:
        number = int(issue.get("number", 0))
        title = str(issue.get("title", "")).strip()
        body = str(issue.get("body") or "").strip()
        revision = str(issue.get("updatedAt") or "missing-updated-at").strip()
        labels = self._label_names(issue.get("labels", []))
        role_matches = [ROLE_LABELS[label] for label in labels if label in ROLE_LABELS]
        role = role_matches[0] if len(role_matches) == 1 else None
        block_reason = None

        if READY_LABEL not in labels:
            block_reason = f"Missing required label: {READY_LABEL}"
        elif len(role_matches) != 1:
            block_reason = "Issue must have exactly one supported agent role label"
        elif not (self.settings.workspace / project.directory / "AGENTS.md").is_file():
            block_reason = "Registered project checkout is missing AGENTS.md"
        else:
            try:
                reject_unsafe_issue_text(f"{title}\n{body}")
            except ValueError as error:
                block_reason = str(error)

        try:
            return self.store.record_issue_intake(
                source="github-label-poller",
                project_key=project.key,
                repository=project.repository,
                issue_number=number,
                revision=revision,
                title=title,
                prompt=body,
                role=role,
                block_reason=block_reason,
            )
        except ValueError as error:
            return self.store.record_issue_intake(
                source="github-label-poller",
                project_key=project.key,
                repository=project.repository,
                issue_number=number,
                revision=revision,
                title=title or f"Blocked GitHub issue #{number}",
                prompt=body,
                role=role,
                block_reason=str(error),
            )

    @staticmethod
    def _label_names(labels: object) -> set[str]:
        if not isinstance(labels, list):
            return set()
        names = set()
        for label in labels:
            if isinstance(label, str):
                names.add(label)
            elif isinstance(label, dict) and isinstance(label.get("name"), str):
                names.add(label["name"])
        return names

    @staticmethod
    def _safe_environment() -> dict[str, str]:
        environment = {
            key: value for key, value in os.environ.items() if key in _SAFE_ENVIRONMENT_KEYS
        }
        environment.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        environment.setdefault("LANG", "C.UTF-8")
        return environment

    def _list_issues(self, project: Project) -> list[dict[str, Any]]:
        completed = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                project.repository,
                "--state",
                "open",
                "--label",
                READY_LABEL,
                "--limit",
                "100",
                "--json",
                "number,title,body,updatedAt,labels",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=self._safe_environment(),
        )
        payload = json.loads(completed.stdout)
        if not isinstance(payload, list):
            raise TypeError("GitHub issue list returned an unexpected payload")
        return payload


class IssueIntakePoller:
    def __init__(self, intake: GitHubIssueIntake, interval_seconds: float = 30):
        if interval_seconds <= 0:
            raise ValueError("Issue intake interval must be positive")
        self.intake = intake
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self._loop, name="github-intake", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=5)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            self.intake.poll_once()
            self.stop_event.wait(self.interval_seconds)
