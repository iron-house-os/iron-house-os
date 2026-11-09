#!/usr/bin/env python3
"""Create and verify deterministic Iron House OS recovery bundle manifests."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

REQUIRED_FILES = ("database.dump", "backend-data.tar.gz")
MANIFEST_NAME = "manifest.json"
FORMAT_VERSION = 1


def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _require_bundle_file(directory: Path, filename: str) -> Path:
    path = directory / filename
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Recovery bundle is missing regular file: {filename}")
    return path


def create_manifest(directory: Path, schema_revision: str) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for filename in REQUIRED_FILES:
        path = _require_bundle_file(directory, filename)
        files[filename] = {"sha256": _digest(path), "size_bytes": path.stat().st_size}
    manifest = {
        "format_version": FORMAT_VERSION,
        "application": "iron-house-os",
        "created_at": datetime.now(UTC).isoformat(),
        "schema_revision": schema_revision,
        "files": files,
    }
    manifest_path = directory / MANIFEST_NAME
    temporary_path = directory / f".{MANIFEST_NAME}.tmp"
    temporary_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temporary_path.replace(manifest_path)
    return manifest


def verify_manifest(directory: Path) -> dict[str, Any]:
    manifest_path = _require_bundle_file(directory, MANIFEST_NAME)
    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Recovery manifest is unreadable: {exc}") from exc
    if manifest.get("format_version") != FORMAT_VERSION:
        raise RuntimeError(f"Unsupported recovery bundle format: {manifest.get('format_version')}")
    if manifest.get("application") != "iron-house-os":
        raise RuntimeError("Recovery bundle application identity is invalid.")
    if not manifest.get("schema_revision"):
        raise RuntimeError("Recovery bundle does not identify its schema revision.")
    expected_files = manifest.get("files")
    if not isinstance(expected_files, dict) or set(expected_files) != set(REQUIRED_FILES):
        raise RuntimeError("Recovery manifest file set is invalid.")
    for filename in REQUIRED_FILES:
        path = _require_bundle_file(directory, filename)
        expected = expected_files[filename]
        actual_size = path.stat().st_size
        if expected.get("size_bytes") != actual_size:
            raise RuntimeError(f"Recovery bundle size mismatch: {filename}")
        if expected.get("sha256") != _digest(path):
            raise RuntimeError(f"Recovery bundle checksum mismatch: {filename}")
    return manifest


def main() -> None:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--directory", type=Path, required=True)
    create.add_argument("--schema-revision", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "create":
        result = create_manifest(args.directory.resolve(), args.schema_revision)
    else:
        result = verify_manifest(args.directory.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
