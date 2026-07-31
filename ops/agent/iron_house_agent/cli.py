from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from .config import Project, load_settings, register_project
from .dashboard import build_state, create_dashboard_server, start_dashboard_thread
from .runtime import AgentRuntime, WorkerPool, supported_roles
from .store import JobStore

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "projects.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Iron House shared agent orchestrator")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Project registry path")
    parser.add_argument("--database", help="Override the SQLite job database path")
    parser.add_argument("--state-directory", help="Override the runtime state directory")
    parser.add_argument("--worktrees-directory", help="Override the isolated worktree directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize state directories and the job database")
    subparsers.add_parser("preflight", help="Verify CLI tools and saved authentication")
    subparsers.add_parser("status", help="Print queue, worker, history, and repository health")
    subparsers.add_parser("run-once", help="Run the next queued job").add_argument(
        "--worker-id", default="manual-worker"
    )

    enqueue = subparsers.add_parser("enqueue", help="Add an issue-linked job to the queue")
    enqueue.add_argument("--project", required=True)
    enqueue.add_argument("--role", required=True, choices=supported_roles())
    enqueue.add_argument("--issue", required=True, type=int)
    enqueue.add_argument("--title", required=True)
    prompt_input = enqueue.add_mutually_exclusive_group(required=True)
    prompt_input.add_argument("--prompt")
    prompt_input.add_argument("--prompt-file", type=Path)

    smoke = subparsers.add_parser("smoke", help="Run a non-destructive Codex feature-branch test")
    smoke.add_argument("--project", required=True)
    smoke.add_argument("--issue", required=True, type=int)

    serve = subparsers.add_parser("serve", help="Run the worker pool and read-only dashboard")
    serve.add_argument("--workers", type=int)

    subparsers.add_parser("dashboard", help="Run only the read-only dashboard")

    register = subparsers.add_parser(
        "register", help="Clone and enroll a policy-ready Iron House repository"
    )
    register.add_argument("--key", required=True)
    register.add_argument("--name", required=True)
    register.add_argument("--repository", required=True, help="GitHub owner/name")
    register.add_argument("--directory", required=True)
    register.add_argument("--default-branch", default="main")
    return parser


def _runtime(arguments: argparse.Namespace) -> AgentRuntime:
    settings = load_settings(arguments.registry)
    if arguments.state_directory:
        settings = replace(settings, state_directory=Path(arguments.state_directory).resolve())
    if arguments.worktrees_directory:
        settings = replace(
            settings, worktrees_directory=Path(arguments.worktrees_directory).resolve()
        )
    database = Path(arguments.database).resolve() if arguments.database else settings.database_path
    store = JobStore(database)
    runtime = AgentRuntime(settings, store)
    runtime.initialize()
    return runtime


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        runtime = _runtime(arguments)
        if arguments.command == "init":
            _print({"status": "initialized", "database": runtime.store.database_path})
            return 0
        if arguments.command == "preflight":
            _print({"status": "ready", "checks": runtime.preflight()})
            return 0
        if arguments.command == "status":
            _print(build_state(runtime.settings, runtime.store))
            return 0
        if arguments.command == "enqueue":
            project = runtime.settings.project(arguments.project)
            prompt = (
                arguments.prompt_file.read_text(encoding="utf-8")
                if arguments.prompt_file
                else arguments.prompt
            )
            job = runtime.store.enqueue(
                project_key=project.key,
                role=arguments.role,
                issue_number=arguments.issue,
                title=arguments.title,
                prompt=prompt,
            )
            _print({key: value for key, value in job.items() if key != "prompt"})
            return 0
        if arguments.command == "run-once":
            job = runtime.run_once(arguments.worker_id)
            _print(
                {"status": "idle"}
                if job is None
                else {k: v for k, v in job.items() if k != "prompt"}
            )
            return 0 if job is None or job["status"] == "succeeded" else 1
        if arguments.command == "smoke":
            runtime.preflight()
            queued = runtime.enqueue_smoke_test(arguments.project, arguments.issue)
            completed = runtime.run_once("smoke-worker")
            _print(
                {
                    "queued_job": queued["id"],
                    "status": completed["status"] if completed else "missing",
                    "branch": completed["branch"] if completed else None,
                    "summary": completed["result_summary"] if completed else None,
                }
            )
            return 0 if completed and completed["status"] == "succeeded" else 1
        if arguments.command == "dashboard":
            server = create_dashboard_server(runtime.settings, runtime.store)
            print(
                f"Dashboard: http://{runtime.settings.dashboard_host}:"
                f"{runtime.settings.dashboard_port}"
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                server.shutdown()
            return 0
        if arguments.command == "serve":
            runtime.preflight()
            workers = arguments.workers or runtime.settings.max_parallel_jobs
            server, dashboard_thread = start_dashboard_thread(runtime.settings, runtime.store)
            pool = WorkerPool(runtime, workers)
            pool.start()
            print(
                f"Workers: {workers}; dashboard: http://{runtime.settings.dashboard_host}:"
                f"{runtime.settings.dashboard_port}"
            )
            try:
                pool.wait()
            finally:
                pool.stop()
                server.shutdown()
                dashboard_thread.join(timeout=5)
            return 0
        if arguments.command == "register":
            project = Project(
                key=arguments.key,
                name=arguments.name,
                repository=arguments.repository,
                directory=arguments.directory,
                default_branch=arguments.default_branch,
            )
            project.validate()
            checkout = runtime.clone_registered_project(project)
            updated = register_project(runtime.settings.registry_path, project)
            _print(
                {
                    "status": "registered",
                    "project": project.key,
                    "checkout": checkout,
                    "project_count": len(updated.projects),
                    "production_deploy_allowed": False,
                }
            )
            return 0
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
