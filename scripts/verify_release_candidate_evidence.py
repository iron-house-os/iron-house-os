#!/usr/bin/env python3
from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path
import re
import sys


PRODUCTION_BASELINE = "55afaa689603263c1ad415436e90cce6679808c3"
REQUIRED_PASSED_GATES = {
    "production": {
        "ci",
        "browser_mobile_accessibility",
        "production_stack_smoke",
        "backup_restore",
    },
    "staging": {
        "staging_configuration",
        "staging_smoke",
        "role_denial",
        "synthetic_data",
        "backup_restore",
        "rollback",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_evidence(
    root: Path,
    evidence_path: Path,
    release_sha: str,
    *,
    profile: str = "production",
) -> dict[str, object]:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    required_gates = REQUIRED_PASSED_GATES[profile]
    if evidence.get("commit_sha") != release_sha:
        raise ValueError("Release evidence commit does not match the approved release.")
    if evidence.get("working_tree_clean") is not True:
        raise ValueError("Release evidence was not generated from a clean working tree.")
    gates = evidence.get("gates")
    if not isinstance(gates, dict):
        raise ValueError("Release evidence gates are missing.")
    failed_gates = sorted(gate for gate in required_gates if gates.get(gate) != "passed")
    if failed_gates:
        raise ValueError(f"Required release gates are not passed: {', '.join(failed_gates)}")
    if profile == "staging":
        if evidence.get("environment") != "staging":
            raise ValueError("Staging evidence must identify the staging environment.")
        if evidence.get("release_id") != release_sha:
            raise ValueError("Staging release ID must be the immutable release commit.")
        baseline = evidence.get("production_baseline")
        if not isinstance(baseline, dict) or baseline.get("commit_sha") != PRODUCTION_BASELINE:
            raise ValueError("Staging evidence does not match the protected production baseline.")
        if baseline.get("comparison") != "read_only":
            raise ValueError("The production baseline comparison must be read-only.")
        rollback = evidence.get("rollback")
        if not isinstance(rollback, dict) or rollback != {
            "outcome": "passed",
            "scope": "staging_only",
        }:
            raise ValueError("Staging-only rollback proof is missing.")
        images = evidence.get("images")
        if not isinstance(images, dict) or any(
            re.fullmatch(r"sha256:[0-9a-f]{64}", str(images.get(service, ""))) is None
            for service in ("backend", "frontend", "postgres")
        ):
            raise ValueError("Immutable staging image IDs are missing.")
        migrations = evidence.get("migrations")
        if not isinstance(migrations, dict) or not migrations.get("alembic"):
            raise ValueError("The staging Alembic revision is missing.")
        if evidence.get("operator_acceptance") != "pending":
            raise ValueError("Staging evidence cannot pre-approve operator acceptance.")
    files = evidence.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Release evidence integrity manifest is missing.")
    for relative_path, expected_digest in files.items():
        path = (root / relative_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Evidence path escapes the repository: {relative_path}") from exc
        if not path.is_file():
            raise ValueError(f"Release evidence file is missing: {relative_path}")
        if sha256(path) != expected_digest:
            raise ValueError(f"Release evidence checksum mismatch: {relative_path}")
    return evidence


def main() -> int:
    parser = ArgumentParser(description="Verify a Build 215/216 release evidence artifact.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--profile", choices=sorted(REQUIRED_PASSED_GATES), default="production")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        evidence = verify_evidence(
            root,
            args.evidence.resolve(),
            args.release,
            profile=args.profile,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"release evidence verification failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "passed",
                "release_sha": evidence["commit_sha"],
                "verified_files": len(evidence["files"]),
                "profile": args.profile,
                "passed_gates": sorted(REQUIRED_PASSED_GATES[args.profile]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
