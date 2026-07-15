#!/usr/bin/env python3
from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path
import sys


REQUIRED_PASSED_GATES = {
    "ci",
    "browser_mobile_accessibility",
    "production_stack_smoke",
    "backup_restore",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_evidence(root: Path, evidence_path: Path, release_sha: str) -> dict[str, object]:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("commit_sha") != release_sha:
        raise ValueError("Release evidence commit does not match the approved release.")
    if evidence.get("working_tree_clean") is not True:
        raise ValueError("Release evidence was not generated from a clean working tree.")
    gates = evidence.get("gates")
    if not isinstance(gates, dict):
        raise ValueError("Release evidence gates are missing.")
    failed_gates = sorted(gate for gate in REQUIRED_PASSED_GATES if gates.get(gate) != "passed")
    if failed_gates:
        raise ValueError(f"Required release gates are not passed: {', '.join(failed_gates)}")
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
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        evidence = verify_evidence(root, args.evidence.resolve(), args.release)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"release evidence verification failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "passed",
                "release_sha": evidence["commit_sha"],
                "verified_files": len(evidence["files"]),
                "passed_gates": sorted(REQUIRED_PASSED_GATES),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
