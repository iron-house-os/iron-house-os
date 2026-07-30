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
    ".env.staging.example",
    "docker-compose.staging.yml",
    "docker-compose.production.yml",
    "docs/operations/cutover-checklist.md",
    "docs/operations/operator-acceptance.md",
    "docs/operations/incident-response.md",
    "docs/operations/rollback.md",
    "docs/operations/recovery.md",
    "docs/operations/v1-staging-environment.md",
    "docs/operations/v1-staging-ipad-acceptance.md",
    "docs/operations/v1-staging-performance-observability.md",
    "docs/operations/v1-staging-release-evidence.md",
    "docs/security/react-router-rsc-advisory.md",
    "ops/digitalocean/host-plan.json",
    "ops/digitalocean/cloud-init.yaml",
    "ops/digitalocean/nginx-maintenance.conf",
    "ops/digitalocean/nginx-live.conf",
    "ops/digitalocean/cutover.sh",
    "scripts/backup.sh",
    "scripts/check_react_router_rsc_boundary.py",
    "scripts/restore.sh",
    "scripts/release_smoke.py",
    "scripts/staging-compose.sh",
    "scripts/staging-smoke-test.sh",
    "scripts/staging_rollback_probe.py",
    "scripts/release_candidate_evidence.py",
    "scripts/verify_release_candidate_evidence.py",
    "scripts/verify_s3_targets.sh",
    "scripts/upload_backup_s3.sh",
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


def parse_assignments(values: Iterable[str], *, label: str) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for value in values:
        try:
            name, assigned = value.split("=", 1)
        except ValueError as exc:
            raise ValueError(f"Invalid {label} '{value}'; expected name=value.") from exc
        if not name or not assigned:
            raise ValueError(f"Invalid {label} '{value}'; expected non-empty name=value.")
        assignments[name] = assigned
    return dict(sorted(assignments.items()))


def build_evidence(
    root: Path,
    *,
    release_id: str | None,
    gates: dict[str, str],
    generated_at: datetime | None = None,
    environment: str = "production",
    images: dict[str, str] | None = None,
    migrations: dict[str, str] | None = None,
    rollback: str = "not_run",
    production_baseline: str | None = None,
    known_limitations: Iterable[str] = (),
) -> dict[str, object]:
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    if missing:
        raise ValueError(f"Release package is incomplete; missing: {', '.join(missing)}")
    commit_sha = git_value(root, "rev-parse", "HEAD")
    resolved_release_id = release_id or commit_sha
    timestamp = generated_at or datetime.now(UTC)
    if environment not in {"production", "staging"}:
        raise ValueError("Environment must be production or staging.")
    if rollback not in ALLOWED_GATE_OUTCOMES:
        raise ValueError(f"Invalid rollback outcome: {rollback}.")
    limitations = [
        "No live host, DNS, TLS, monitoring destination, or paid service was provisioned.",
        "Operator acceptance must be completed at the approved cutover window.",
        *known_limitations,
    ]
    return {
        "schema_version": 2,
        "release_id": resolved_release_id,
        "commit_sha": commit_sha,
        "commit_tree": git_value(root, "rev-parse", "HEAD^{tree}"),
        "generated_at": timestamp.astimezone(UTC).isoformat(),
        "working_tree_clean": not bool(git_value(root, "status", "--porcelain")),
        "environment": environment,
        "gates": gates,
        "images": dict(sorted((images or {}).items())),
        "migrations": dict(sorted((migrations or {}).items())),
        "production_baseline": {
            "commit_sha": production_baseline or commit_sha,
            "comparison": "read_only" if environment == "staging" else "release_candidate",
        },
        "rollback": {
            "outcome": rollback,
            "scope": "staging_only" if environment == "staging" else "not_applicable",
        },
        "files": {path: sha256(root / path) for path in REQUIRED_FILES},
        "operator_acceptance": "pending",
        "limitations": limitations,
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
        f"- Environment: `{evidence['environment']}`",
        f"- Working tree clean: {str(evidence['working_tree_clean']).lower()}",
        f"- Operator acceptance: **{evidence['operator_acceptance']}**",
        (
            "- Production baseline: "
            f"`{evidence['production_baseline']['commit_sha']}` "
            f"({evidence['production_baseline']['comparison']})"
        ),
        (
            "- Rollback: "
            f"**{evidence['rollback']['outcome']}** "
            f"({evidence['rollback']['scope']})"
        ),
        "",
        "## Gates",
        "",
        *[f"- {name}: **{outcome}**" for name, outcome in gates.items()],
        "",
        "## Images",
        "",
        *[f"- {name}: `{reference}`" for name, reference in evidence["images"].items()],
        "",
        "## Migrations",
        "",
        *[f"- {name}: `{revision}`" for name, revision in evidence["migrations"].items()],
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
    parser.add_argument("--environment", choices=("production", "staging"), default="production")
    parser.add_argument("--image", action="append", default=[], metavar="NAME=REFERENCE")
    parser.add_argument("--migration", action="append", default=[], metavar="NAME=REVISION")
    parser.add_argument("--rollback", choices=sorted(ALLOWED_GATE_OUTCOMES), default="not_run")
    parser.add_argument("--production-baseline")
    parser.add_argument("--known-limitation", action="append", default=[])
    args = parser.parse_args()
    try:
        gates = parse_gates(args.gate)
        images = parse_assignments(args.image, label="image")
        migrations = parse_assignments(args.migration, label="migration")
        evidence = build_evidence(
            args.root.resolve(),
            release_id=args.release_id,
            gates=gates,
            environment=args.environment,
            images=images,
            migrations=migrations,
            rollback=args.rollback,
            production_baseline=args.production_baseline,
            known_limitations=args.known_limitation,
        )
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
