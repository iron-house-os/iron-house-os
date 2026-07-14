#!/usr/bin/env python3
from argparse import ArgumentParser
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterable

REQUIRED_FILES = (
    ".env.production.example",
    "docker-compose.production.yml",
    "docs/operations/cutover-checklist.md",
    "docs/operations/operator-acceptance.md",
    "docs/operations/incident-response.md",
    "docs/operations/rollback.md",
    "docs/operations/recovery.md",
    "scripts/backup.sh",
    "scripts/restore.sh",
    "scripts/release_smoke.py",
)
ALLOWED_GATE_OUTCOMES = {"passed", "failed", "not_run"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def parse_gates(values: Iterable[str]) -> dict[str, str]:
    gates: dict[str, str] = {}
    for value in values:
        try:
            name, outcome = value.split("=", 1)
        except ValueError as exc:
            raise ValueError(f"Invalid gate '{value}'; expected name=outcome.") from exc
        if not name or outcome not in ALLOWED_GATE_OUTCOMES:
            raise ValueError(
                f"Invalid gate '{value}'; outcomes are {sorted(ALLOWED_GATE_OUTCOMES)}."
            )
        gates[name] = outcome
    return dict(sorted(gates.items()))


def build_evidence(
    root: Path,
    *,
    release_id: str | None,
    gates: dict[str, str],
    generated_at: datetime | None = None,
) -> dict[str, object]:
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    if missing:
        raise ValueError(f"Release package is incomplete; missing: {', '.join(missing)}")
    commit_sha = git_value(root, "rev-parse", "HEAD")
    resolved_release_id = release_id or commit_sha
    timestamp = generated_at or datetime.now(UTC)
    return {
        "schema_version": 1,
        "release_id": resolved_release_id,
        "commit_sha": commit_sha,
        "commit_tree": git_value(root, "rev-parse", "HEAD^{tree}"),
        "generated_at": timestamp.astimezone(UTC).isoformat(),
        "working_tree_clean": not bool(git_value(root, "status", "--porcelain")),
        "gates": gates,
        "files": {path: sha256(root / path) for path in REQUIRED_FILES},
        "operator_acceptance": "pending",
        "limitations": [
            "No live host, DNS, TLS, monitoring destination, or paid service was provisioned.",
            "Operator acceptance must be completed at the approved cutover window.",
        ],
    }


def render_markdown(evidence: dict[str, object]) -> str:
    gates = evidence["gates"]
    files = evidence["files"]
    lines = [
        "# Iron House OS release-candidate evidence",
        "",
        f"- Release ID: `{evidence['release_id']}`",
        f"- Commit: `{evidence['commit_sha']}`",
        f"- Tree: `{evidence['commit_tree']}`",
        f"- Generated: {evidence['generated_at']}",
        f"- Working tree clean: {str(evidence['working_tree_clean']).lower()}",
        f"- Operator acceptance: **{evidence['operator_acceptance']}**",
        "",
        "## Gates",
        "",
        *[f"- {name}: **{outcome}**" for name, outcome in gates.items()],
        "",
        "## Integrity manifest",
        "",
        *[f"- `{path}` — `{digest}`" for path, digest in files.items()],
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in evidence["limitations"]],
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = ArgumentParser(description="Build an integrity-checked IHOS release evidence bundle.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("release-candidate-evidence"))
    parser.add_argument("--release-id")
    parser.add_argument("--gate", action="append", default=[], metavar="NAME=OUTCOME")
    args = parser.parse_args()
    try:
        gates = parse_gates(args.gate)
        evidence = build_evidence(args.root.resolve(), release_id=args.release_id, gates=gates)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"release evidence failed: {exc}", file=sys.stderr)
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output / "evidence.md").write_text(render_markdown(evidence), encoding="utf-8")
    print(f"release evidence written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
