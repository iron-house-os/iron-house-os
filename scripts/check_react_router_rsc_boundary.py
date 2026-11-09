#!/usr/bin/env python3
"""Fail closed if Iron House OS begins using React Router's unstable RSC path."""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys
from typing import Any


ADVISORY = "GHSA-qwww-vcr4-c8h2"
FORBIDDEN_DEPENDENCIES = {
    "@react-router/dev",
    "@react-router/node",
    "@react-router/serve",
    "@vitejs/plugin-rsc",
    "react-server-dom-parcel",
    "react-server-dom-turbopack",
    "react-server-dom-webpack",
}
FORBIDDEN_TOKENS = {
    '"use server"': "React server-function directive",
    "'use server'": "React server-function directive",
    "@vitejs/plugin-rsc": "experimental Vite RSC plugin",
    "RSCHydratedRouter": "React Router RSC client router",
    "RSCStaticRouter": "React Router RSC server router",
    "createCallServer": "React Router RSC call-server API",
    "getRSCStream": "React Router RSC stream API",
    "matchRSCServerRequest": "React Router RSC server-request API",
    "routeRSCServerRequest": "React Router RSC server-request API",
    "unstable_reactRouterRSC": "React Router unstable RSC Vite plugin",
}
PACKAGE_SECTIONS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)
SOURCE_SUFFIXES = {".js", ".jsx", ".mjs", ".mts", ".ts", ".tsx"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def scanned_files(frontend: Path) -> list[Path]:
    files = [
        path
        for path in (frontend / "src").rglob("*")
        if path.is_file() and path.suffix in SOURCE_SUFFIXES
    ]
    for pattern in (
        "vite.config.*",
        "react-router.config.*",
        "entry.client.*",
        "entry.server.*",
    ):
        files.extend(path for path in frontend.glob(pattern) if path.is_file())
    return sorted(set(files))


def locked_version(lock: dict[str, Any], package: str) -> str | None:
    package_record = lock.get("packages", {}).get(f"node_modules/{package}", {})
    version = package_record.get("version")
    return version if isinstance(version, str) else None


def inspect_boundary(root: Path) -> dict[str, Any]:
    frontend = root / "frontend"
    package_path = frontend / "package.json"
    lock_path = frontend / "package-lock.json"
    if not package_path.is_file() or not lock_path.is_file():
        raise ValueError("frontend/package.json and frontend/package-lock.json are required.")

    package = load_json(package_path)
    lock = load_json(lock_path)
    errors: list[str] = []

    for section in PACKAGE_SECTIONS:
        dependencies = package.get(section, {})
        if not isinstance(dependencies, dict):
            errors.append(f"frontend/package.json {section} must be an object.")
            continue
        for dependency in sorted(FORBIDDEN_DEPENDENCIES.intersection(dependencies)):
            errors.append(f"Forbidden RSC dependency in {section}: {dependency}")

    files = scanned_files(frontend)
    for path in files:
        content = path.read_text(encoding="utf-8")
        for token, meaning in FORBIDDEN_TOKENS.items():
            if token in content:
                relative = path.relative_to(root)
                errors.append(f"{relative}: {meaning} detected ({token})")

    result = {
        "advisory": ADVISORY,
        "architecture": "vite-declarative-spa",
        "locked_versions": {
            "react-router": locked_version(lock, "react-router"),
            "react-router-dom": locked_version(lock, "react-router-dom"),
        },
        "rsc_dependencies": "absent",
        "rsc_source_apis": "absent",
        "scanned_files": len(files),
        "status": "passed" if not errors else "failed",
        "errors": errors,
    }
    return result


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    try:
        result = inspect_boundary(args.root.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"React Router RSC boundary check failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
