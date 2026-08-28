#!/usr/bin/env python3
"""Fail closed when GitHub workflows use mutable or unapproved actions."""

from argparse import ArgumentParser
import json
from pathlib import Path
import re
import sys
from typing import Any


APPROVED_REMOTE_ACTIONS = {
    "actions/checkout": {
        "sha": "11d5960a326750d5838078e36cf38b85af677262",
        "version": "v4",
    },
    "actions/setup-node": {
        "sha": "49933ea5288caeca8642d1e84afbd3f7d6820020",
        "version": "v4",
    },
    "actions/setup-python": {
        "sha": "a26af69be951a213d495a4c3e4e4022e16d87065",
        "version": "v5",
    },
    "actions/upload-artifact": {
        "sha": "ea165f8d65b6e75b540449e92b4886f43607fa02",
        "version": "v4",
    },
}
FULL_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
REMOTE_ACTION = re.compile(r"^(?P<action>[^@\s]+)@(?P<ref>[^@\s]+)$")
USES_LINE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*(?P<value>[^\s#]+)(?:\s+#\s*(?P<comment>.*?))?\s*$"
)
USES_PREFIX = re.compile(r"^\s*(?:-\s*)?uses:")


def workflow_files(root: Path) -> list[Path]:
    workflow_root = root / ".github" / "workflows"
    return sorted(
        {
            *workflow_root.glob("*.yml"),
            *workflow_root.glob("*.yaml"),
        }
    )


def _check_local_action(root: Path, workflow: Path, line_number: int, value: str) -> list[str]:
    if not value.startswith("./.github/actions/"):
        return [
            f"{workflow.relative_to(root)}:{line_number}: local action must be under "
            f"./.github/actions/: {value}"
        ]

    relative = Path(value.removeprefix("./"))
    candidate = (root / relative).resolve()
    actions_root = (root / ".github" / "actions").resolve()
    try:
        candidate.relative_to(actions_root)
    except ValueError:
        return [
            f"{workflow.relative_to(root)}:{line_number}: local action escapes "
            f".github/actions: {value}"
        ]

    if not candidate.is_dir() or not any(
        (candidate / manifest).is_file() for manifest in ("action.yml", "action.yaml")
    ):
        return [
            f"{workflow.relative_to(root)}:{line_number}: local action has no "
            f"action.yml or action.yaml: {value}"
        ]
    return []


def _check_remote_action(
    root: Path,
    workflow: Path,
    line_number: int,
    value: str,
    comment: str | None,
) -> list[str]:
    relative = workflow.relative_to(root)
    match = REMOTE_ACTION.fullmatch(value)
    if not match:
        return [f"{relative}:{line_number}: malformed remote action reference: {value}"]

    action = match.group("action")
    ref = match.group("ref")
    errors: list[str] = []
    if not FULL_COMMIT_SHA.fullmatch(ref):
        errors.append(
            f"{relative}:{line_number}: remote action must use a full 40-character "
            f"commit SHA: {value}"
        )

    approved = APPROVED_REMOTE_ACTIONS.get(action)
    if approved is None:
        errors.append(
            f"{relative}:{line_number}: remote action is not in the approved allowlist: {action}"
        )
        return errors

    if ref != approved["sha"]:
        errors.append(
            f"{relative}:{line_number}: {action} must use approved SHA "
            f"{approved['sha']}, got {ref}"
        )

    version = approved["version"]
    comment_version = (comment or "").strip().split(maxsplit=1)[0:1]
    if comment_version != [version]:
        errors.append(
            f"{relative}:{line_number}: pinned {action} must retain '# {version}' "
            "for update visibility"
        )
    return errors


def inspect_workflows(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = workflow_files(root)
    errors: list[str] = []
    action_references = 0

    if not files:
        errors.append("No GitHub workflow files were found under .github/workflows.")

    for workflow in files:
        try:
            lines = workflow.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            errors.append(f"{workflow.relative_to(root)}: unable to read workflow: {exc}")
            continue

        if not any(line.startswith("permissions:") for line in lines):
            errors.append(
                f"{workflow.relative_to(root)}: missing explicit top-level permissions"
            )

        for line_number, line in enumerate(lines, start=1):
            if not USES_PREFIX.match(line):
                continue
            action_references += 1
            match = USES_LINE.fullmatch(line)
            if not match:
                errors.append(
                    f"{workflow.relative_to(root)}:{line_number}: malformed uses declaration"
                )
                continue

            value = match.group("value")
            if value.startswith("./"):
                errors.extend(_check_local_action(root, workflow, line_number, value))
                continue
            if value.startswith("docker://"):
                errors.append(
                    f"{workflow.relative_to(root)}:{line_number}: docker actions require "
                    "an explicit approved digest policy before use"
                )
                continue
            errors.extend(
                _check_remote_action(
                    root,
                    workflow,
                    line_number,
                    value,
                    match.group("comment"),
                )
            )

    return {
        "action_references": action_references,
        "approved_remote_actions": {
            action: details["sha"] for action, details in APPROVED_REMOTE_ACTIONS.items()
        },
        "errors": errors,
        "status": "passed" if not errors else "failed",
        "workflow_files": len(files),
    }


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    try:
        result = inspect_workflows(args.root)
    except OSError as exc:
        print(f"Workflow security check failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
