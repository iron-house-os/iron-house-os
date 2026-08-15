#!/usr/bin/env python3
"""Create a post-backup marker and prove that a staging restore removes it."""

from argparse import ArgumentParser
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

from release_smoke import _json_request, build_smoke_opener


def _login(base_url: str, opener, email: str, password: str) -> None:
    session = _json_request(
        base_url,
        "/api/v1/auth/login",
        opener=opener,
        method="POST",
        payload={"email": email, "password": password},
    )
    if session.get("authentication") != "authenticated":
        raise RuntimeError(f"Rollback probe login failed: {session}")


def create_marker(base_url: str, email: str, password: str, output: Path) -> dict[str, str]:
    opener = build_smoke_opener(base_url)
    _login(base_url, opener, email, password)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    project = _json_request(
        base_url,
        "/api/v1/projects",
        opener=opener,
        method="POST",
        payload={
            "name": f"Sprint 1E post-backup rollback marker {stamp}",
            "municipality": "Staging only",
            "project_number": f"STAGING-ROLLBACK-{stamp}",
        },
        expected=(201,),
    )
    result = {"project_id": project["id"], "project_name": project["name"]}
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def verify_absent(base_url: str, email: str, password: str, source: Path) -> dict[str, str]:
    expected = json.loads(source.read_text(encoding="utf-8"))
    opener = build_smoke_opener(base_url)
    _login(base_url, opener, email, password)
    request = Request(
        f"{base_url.rstrip('/')}/api/v1/projects/{expected['project_id']}",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=30) as response:
            response_body = response.read().decode(errors="replace")
    except HTTPError as exc:
        if exc.code == 404:
            return {
                "status": "passed",
                "rollback_marker": expected["project_id"],
                "result": "absent_after_restore",
            }
        raise RuntimeError(
            f"Rollback marker lookup returned {exc.code}; expected 404."
        ) from exc
    raise RuntimeError(
        "Staging rollback failed: post-backup marker still exists after restore: "
        f"{response.status} {response_body}"
    )


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("command", choices=("create", "verify-absent"))
    parser.add_argument("--base-url", default=os.getenv("IHOS_BASE_URL", "http://127.0.0.1:8081"))
    parser.add_argument("--email", default=os.getenv("BOOTSTRAP_ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.getenv("BOOTSTRAP_ADMIN_PASSWORD"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    if not args.email or not args.password:
        raise SystemExit("BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD are required.")
    if args.command == "create":
        if args.output is None:
            raise SystemExit("--output is required for create.")
        result = create_marker(args.base_url, args.email, args.password, args.output)
    else:
        if args.input is None:
            raise SystemExit("--input is required for verify-absent.")
        result = verify_absent(args.base_url, args.email, args.password, args.input)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
