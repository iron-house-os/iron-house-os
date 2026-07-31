from __future__ import annotations

import os
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")
AGENT_ROLES = (
    "build",
    "ci-repair",
    "code-review",
    "qa-browser",
    "security-audit",
    "dependency-update",
    "documentation",
    "issue-planning",
)
_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\b(?:OPENAI_API_KEY|CODEX_API_KEY|GH_TOKEN)\s*=\s*\S+", re.IGNORECASE),
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def reject_embedded_secrets(value: str) -> None:
    if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
        raise ValueError("Task text appears to contain a secret; use saved CLI credentials instead")


class JobStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        os.chmod(self.database_path, 0o600)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_key TEXT NOT NULL,
                    role TEXT NOT NULL,
                    issue_number INTEGER NOT NULL CHECK (issue_number > 0),
                    title TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'standard' CHECK (mode IN ('standard', 'smoke')),
                    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
                    branch TEXT,
                    worktree TEXT,
                    worker_id TEXT,
                    log_path TEXT,
                    result_summary TEXT,
                    exit_code INTEGER,
                    queued_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS jobs_status_queue_idx ON jobs(status, queued_at);
                CREATE TABLE IF NOT EXISTS workers (
                    id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    current_job_id TEXT,
                    heartbeat_at TEXT NOT NULL,
                    FOREIGN KEY(current_job_id) REFERENCES jobs(id)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    event TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
                CREATE TABLE IF NOT EXISTS intake_sources (
                    project_key TEXT PRIMARY KEY,
                    state TEXT NOT NULL CHECK (state IN ('ready', 'blocked')),
                    detail TEXT NOT NULL,
                    checked_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS issue_intake (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    project_key TEXT NOT NULL,
                    repository TEXT NOT NULL,
                    issue_number INTEGER NOT NULL CHECK (issue_number > 0),
                    revision TEXT NOT NULL,
                    role TEXT,
                    status TEXT NOT NULL CHECK (status IN ('accepted', 'blocked')),
                    detail TEXT NOT NULL,
                    job_id TEXT,
                    discovered_at TEXT NOT NULL,
                    UNIQUE(source, repository, issue_number, revision),
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
                CREATE INDEX IF NOT EXISTS issue_intake_recent_idx
                    ON issue_intake(discovered_at DESC);
                """
            )

    @staticmethod
    def _validate_job(*, role: str, issue_number: int, title: str, prompt: str, mode: str) -> None:
        if role not in AGENT_ROLES:
            raise ValueError(f"Unsupported agent role: {role}")
        if issue_number <= 0:
            raise ValueError("An issue number is required for every agent job")
        if not title.strip() or len(title) > 160:
            raise ValueError("Job title must contain 1 to 160 characters")
        if not prompt.strip():
            raise ValueError("Job prompt cannot be empty")
        if mode not in {"standard", "smoke"}:
            raise ValueError(f"Unsupported job mode: {mode}")
        reject_embedded_secrets(title)
        reject_embedded_secrets(prompt)

    def enqueue(
        self,
        *,
        project_key: str,
        role: str,
        issue_number: int,
        title: str,
        prompt: str,
        mode: str = "standard",
    ) -> dict[str, Any]:
        self._validate_job(
            role=role,
            issue_number=issue_number,
            title=title,
            prompt=prompt,
            mode=mode,
        )
        job_id = str(uuid.uuid4())
        queued_at = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, project_key, role, issue_number, title, prompt, mode, status, queued_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                """,
                (
                    job_id,
                    project_key,
                    role,
                    issue_number,
                    title.strip(),
                    prompt.strip(),
                    mode,
                    queued_at,
                ),
            )
            self._event(connection, job_id, "queued", f"role={role}")
        return self.get_job(job_id)

    def record_issue_intake(
        self,
        *,
        source: str,
        project_key: str,
        repository: str,
        issue_number: int,
        revision: str,
        title: str,
        prompt: str,
        role: str | None,
        block_reason: str | None = None,
    ) -> dict[str, Any]:
        if not source.strip() or not repository.strip() or not revision.strip():
            raise ValueError("Issue intake source, repository, and revision are required")
        if issue_number <= 0:
            raise ValueError("Issue intake requires a positive issue number")
        if block_reason is None:
            if role is None:
                raise ValueError("Accepted issue intake requires an agent role")
            self._validate_job(
                role=role,
                issue_number=issue_number,
                title=title,
                prompt=prompt,
                mode="standard",
            )
        discovered_at = utc_now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT * FROM issue_intake
                WHERE source = ? AND repository = ? AND issue_number = ? AND revision = ?
                """,
                (source, repository, issue_number, revision),
            ).fetchone()
            if existing is not None:
                connection.execute("COMMIT")
                return {**dict(existing), "duplicate": True}

            job_id = None
            status = "blocked" if block_reason else "accepted"
            detail = (block_reason or "Queued from explicitly labelled GitHub issue")[:1000]
            if block_reason is None:
                job_id = str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO jobs (
                        id, project_key, role, issue_number, title, prompt, mode, status, queued_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'standard', 'queued', ?)
                    """,
                    (
                        job_id,
                        project_key,
                        role,
                        issue_number,
                        title.strip(),
                        prompt.strip(),
                        discovered_at,
                    ),
                )
                self._event(connection, job_id, "queued", f"role={role}; source=github-intake")
            cursor = connection.execute(
                """
                INSERT INTO issue_intake (
                    source, project_key, repository, issue_number, revision, role,
                    status, detail, job_id, discovered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    project_key,
                    repository,
                    issue_number,
                    revision,
                    role,
                    status,
                    detail,
                    job_id,
                    discovered_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM issue_intake WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            connection.execute("COMMIT")
        return {**dict(row), "duplicate": False}

    def update_intake_source(self, project_key: str, state: str, detail: str) -> None:
        if state not in {"ready", "blocked"}:
            raise ValueError(f"Unsupported intake source state: {state}")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO intake_sources (project_key, state, detail, checked_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_key) DO UPDATE SET
                    state = excluded.state,
                    detail = excluded.detail,
                    checked_at = excluded.checked_at
                """,
                (project_key, state, detail[:1000], utc_now()),
            )

    def claim_next(self, worker_id: str) -> dict[str, Any] | None:
        now = utc_now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE status = 'queued' ORDER BY queued_at, id LIMIT 1"
            ).fetchone()
            if row is None:
                connection.execute("COMMIT")
                self.heartbeat(worker_id, "idle", None)
                return None
            updated = connection.execute(
                """
                UPDATE jobs
                SET status = 'running', worker_id = ?, started_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (worker_id, now, row["id"]),
            )
            if updated.rowcount != 1:
                connection.execute("ROLLBACK")
                return None
            self._event(connection, row["id"], "claimed", f"worker={worker_id}")
            connection.execute("COMMIT")
        self.heartbeat(worker_id, "running", row["id"])
        return self.get_job(row["id"])

    def set_execution_metadata(
        self, job_id: str, *, branch: str, worktree: str, log_path: str
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE jobs SET branch = ?, worktree = ?, log_path = ? WHERE id = ?",
                (branch, worktree, log_path, job_id),
            )
            self._event(connection, job_id, "worktree-ready", branch)

    def finish(self, job_id: str, *, exit_code: int, summary: str) -> None:
        status = "succeeded" if exit_code == 0 else "failed"
        now = utc_now()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT worker_id FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, exit_code = ?, result_summary = ?, finished_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (status, exit_code, summary[:1000], now, job_id),
            )
            self._event(connection, job_id, status, f"exit_code={exit_code}")
            worker_id = row["worker_id"]
        if worker_id:
            self.heartbeat(worker_id, "idle", None)

    def fail(self, job_id: str, message: str, exit_code: int = 1) -> None:
        self.finish(job_id, exit_code=exit_code, summary=message)

    def heartbeat(self, worker_id: str, state: str, current_job_id: str | None) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO workers (id, state, current_job_id, heartbeat_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state = excluded.state,
                    current_job_id = excluded.current_job_id,
                    heartbeat_at = excluded.heartbeat_at
                """,
                (worker_id, state, current_job_id, utc_now()),
            )

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return dict(row)

    def snapshot(self, history_limit: int = 25) -> dict[str, Any]:
        with self.connect() as connection:
            running = self._public_jobs(
                connection.execute(
                    "SELECT * FROM jobs WHERE status = 'running' ORDER BY started_at"
                ).fetchall()
            )
            queued = self._public_jobs(
                connection.execute(
                    "SELECT * FROM jobs WHERE status = 'queued' ORDER BY queued_at"
                ).fetchall()
            )
            history = self._public_jobs(
                connection.execute(
                    """
                    SELECT * FROM jobs
                    WHERE status IN ('succeeded', 'failed', 'cancelled')
                    ORDER BY finished_at DESC LIMIT ?
                    """,
                    (history_limit,),
                ).fetchall()
            )
            workers = [
                dict(row)
                for row in connection.execute("SELECT * FROM workers ORDER BY id").fetchall()
            ]
            intake_sources = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM intake_sources ORDER BY project_key"
                ).fetchall()
            ]
            intake_history = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT project_key, repository, issue_number, revision, role, status,
                           detail, job_id, discovered_at
                    FROM issue_intake ORDER BY discovered_at DESC, id DESC LIMIT ?
                    """,
                    (history_limit,),
                ).fetchall()
            ]
        return {
            "workers": workers,
            "current_jobs": running,
            "queue": queued,
            "history": history,
            "intake_sources": intake_sources,
            "intake_history": intake_history,
        }

    @staticmethod
    def _public_jobs(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        private_fields = {"prompt"}
        return [
            {key: value for key, value in dict(row).items() if key not in private_fields}
            for row in rows
        ]

    @staticmethod
    def _event(
        connection: sqlite3.Connection, job_id: str | None, event: str, detail: str | None
    ) -> None:
        connection.execute(
            "INSERT INTO events (job_id, event, detail, created_at) VALUES (?, ?, ?, ?)",
            (job_id, event, detail, utc_now()),
        )
