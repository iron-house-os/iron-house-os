#!/usr/bin/env python3
"""Fail CI when the approved Iron House visual baseline changes unexpectedly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "frontend" / "visual-design-lock.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        protected_files = manifest["files"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"visual design lock is invalid: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for relative_path, expected_hash in sorted(protected_files.items()):
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing protected file: {relative_path}")
            continue
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            failures.append(
                f"protected appearance changed: {relative_path}\n"
                f"  approved: {expected_hash}\n"
                f"  current:  {actual_hash}"
            )

    if failures:
        print("Iron House OS visual design lock failed.", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        print(
            "Significant appearance changes require Jeremie Peters' explicit written approval "
            "and an intentional manifest update. See docs/visual-design-lock.md.",
            file=sys.stderr,
        )
        return 1

    print(
        "Iron House OS visual design lock passed "
        f"({len(protected_files)} protected files, baseline {manifest['baseline_commit'][:8]})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
