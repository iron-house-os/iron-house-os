#!/usr/bin/env python3
"""Verify recovery bundles and prune only those outside the retention policy."""

from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import shutil

from recovery_manifest import verify_manifest


@dataclass(frozen=True)
class RecoveryBundle:
    path: Path
    created_at: datetime


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def discover_verified_bundles(root: Path) -> list[RecoveryBundle]:
    bundles: list[RecoveryBundle] = []
    if not root.is_dir():
        return bundles
    for child in sorted(root.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_symlink() or not child.is_dir():
            raise RuntimeError(f"Unexpected item in backup root: {child.name}")
        manifest = verify_manifest(child)
        bundles.append(RecoveryBundle(path=child, created_at=_timestamp(manifest["created_at"])))
    return sorted(bundles, key=lambda bundle: bundle.created_at, reverse=True)


def retention_candidates(
    bundles: list[RecoveryBundle],
    *,
    now: datetime,
    retention_days: int,
    keep_minimum: int,
    maximum_bundles: int,
) -> list[RecoveryBundle]:
    if retention_days < 1 or keep_minimum < 1 or maximum_bundles < keep_minimum:
        raise ValueError("Retention values must be positive and maximum_bundles must cover keep_minimum.")
    cutoff = now - timedelta(days=retention_days)
    return [
        bundle
        for index, bundle in enumerate(bundles)
        if index >= keep_minimum
        and (bundle.created_at < cutoff or index >= maximum_bundles)
    ]


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--keep-minimum", type=int, default=7)
    parser.add_argument("--maximum-bundles", type=int, default=60)
    parser.add_argument("--now", type=_timestamp, default=datetime.now(UTC))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    bundles = discover_verified_bundles(root)
    candidates = retention_candidates(
        bundles,
        now=args.now,
        retention_days=args.retention_days,
        keep_minimum=args.keep_minimum,
        maximum_bundles=args.maximum_bundles,
    )
    if args.apply:
        for bundle in candidates:
            shutil.rmtree(bundle.path)
    print(
        json.dumps(
            {
                "verified_bundles": len(bundles),
                "deleted": [bundle.path.name for bundle in candidates] if args.apply else [],
                "deletion_candidates": [bundle.path.name for bundle in candidates],
                "applied": args.apply,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
