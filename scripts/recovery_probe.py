#!/usr/bin/env python3
"""Create or verify a database-and-upload sentinel around a recovery drill."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
from urllib.request import HTTPCookieProcessor, build_opener

from release_smoke import _json_request, _minimal_pdf, _multipart


def _login(base_url: str, opener, email: str, password: str) -> None:
    session = _json_request(
        base_url,
        "/api/v1/auth/login",
        opener=opener,
        method="POST",
        payload={"email": email, "password": password},
    )
    if session.get("authentication") != "authenticated":
        raise RuntimeError(f"Recovery probe login failed: {session}")


def create_probe(base_url: str, email: str, password: str, output: Path) -> dict:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    _login(base_url, opener, email, password)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    project = _json_request(
        base_url,
        "/api/v1/projects",
        opener=opener,
        method="POST",
        payload={
            "name": f"Build 209 recovery sentinel {stamp}",
            "municipality": "Surrey",
            "project_number": f"RECOVERY-{stamp}",
        },
        expected=(201,),
    )
    pdf = _minimal_pdf(f"Build 209 recovery sentinel {stamp}")
    body, content_type = _multipart(
        {"project_id": project["id"], "title": "Build 209 recovery sentinel", "municipality": "Surrey"},
        "build-209-recovery-sentinel.pdf",
        pdf,
    )
    drawing = _json_request(
        base_url,
        "/api/v1/drawing-intelligence/ingest",
        opener=opener,
        method="POST",
        body=body,
        content_type=content_type,
        expected=(201,),
    )
    result = {
        "project_id": project["id"],
        "project_name": project["name"],
        "document_id": drawing["source"]["document_id"],
        "sha256_hash": drawing["source"]["sha256_hash"],
        "size_bytes": drawing["source"]["size_bytes"],
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def verify_probe(base_url: str, email: str, password: str, source: Path) -> dict:
    expected = json.loads(source.read_text())
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    _login(base_url, opener, email, password)
    project = _json_request(
        base_url,
        f"/api/v1/projects/{expected['project_id']}",
        opener=opener,
    )
    integrity = _json_request(
        base_url,
        f"/api/v1/documents/{expected['document_id']}/integrity",
        opener=opener,
    )
    if project.get("name") != expected["project_name"]:
        raise RuntimeError(f"Restored project does not match the recovery sentinel: {project}")
    if not integrity.get("file_exists"):
        raise RuntimeError(f"Restored recovery sentinel upload is missing: {integrity}")
    if integrity.get("sha256_hash") != expected["sha256_hash"]:
        raise RuntimeError(f"Restored recovery sentinel checksum differs: {integrity}")
    if integrity.get("size_bytes") != expected["size_bytes"]:
        raise RuntimeError(f"Restored recovery sentinel size differs: {integrity}")
    return {"status": "passed", "project_id": project["id"], "document_integrity": integrity}


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("command", choices=("create", "verify"))
    parser.add_argument("--base-url", default=os.getenv("IHOS_BASE_URL", "http://127.0.0.1:8080"))
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
        result = create_probe(args.base_url, args.email, args.password, args.output)
    else:
        if args.input is None:
            raise SystemExit("--input is required for verify.")
        result = verify_probe(args.base_url, args.email, args.password, args.input)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
