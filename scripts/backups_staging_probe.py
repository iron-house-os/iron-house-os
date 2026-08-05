#!/usr/bin/env python3
"""Prove the Backups intake boundary against a disposable staging stack."""

from argparse import ArgumentParser
import base64
from http.cookiejar import CookieJar
import json
import os
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4

from release_smoke import _json_request, _request

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _multipart_image(fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = f"ihos-backups-{uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            value.encode(),
            b"\r\n",
        ])
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="file"; filename="backups-staging.png"\r\n',
        b"Content-Type: image/png\r\n\r\n",
        PNG,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def run(base_url: str, email: str, password: str) -> dict:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    session = _json_request(
        base_url,
        "/api/v1/auth/login",
        opener=opener,
        method="POST",
        payload={"email": email, "password": password},
    )
    if session.get("authentication") != "authenticated":
        raise RuntimeError(f"Backups staging login failed: {session}")

    body, content_type = _multipart_image({
        "note": "Disposable staging Backups probe",
        "project_hint": "Text-only staging hint",
    })
    intake = _json_request(
        base_url,
        "/api/v1/backups",
        opener=opener,
        method="POST",
        body=body,
        content_type=content_type,
        expected=(201,),
    )
    if intake.get("status") != "pending" or not intake.get("media_asset_id"):
        raise RuntimeError(f"Backups upload did not persist a pending intake: {intake}")

    controller = _json_request(
        base_url,
        "/api/v1/backups/controller/daily",
        opener=opener,
        method="POST",
        payload={},
    )
    if controller.get("selected", 0) < 1:
        raise RuntimeError(f"Backups controller did not select the probe: {controller}")
    routed = _json_request(
        base_url,
        f"/api/v1/backups/{intake['id']}",
        opener=opener,
    )
    if routed.get("status") != "needs_review" or routed.get("destination_record_id") is not None:
        raise RuntimeError(f"Uncertain Backups probe was not kept in management triage: {routed}")
    actions = {event.get("action") for event in routed.get("audit_history", [])}
    required_actions = {"uploaded", "processing_started", "triage_required"}
    if not required_actions.issubset(actions):
        raise RuntimeError(f"Backups audit trail is incomplete: {routed.get('audit_history')}")

    status_code, original = _request(
        base_url,
        f"/api/v1/media/{intake['media_asset_id']}/content",
        opener=opener,
    )
    if status_code != 200 or original != PNG:
        raise RuntimeError("Authorized Backups original-image read did not preserve exact bytes.")
    anonymous = build_opener(HTTPCookieProcessor(CookieJar()))
    try:
        anonymous.open(Request(
            f"{base_url.rstrip('/')}/api/v1/media/{intake['media_asset_id']}/content"
        ), timeout=30)
    except HTTPError as exc:
        if exc.code != 401:
            raise RuntimeError(f"Anonymous original-image read returned {exc.code}, expected 401.") from exc
    else:
        raise RuntimeError("Anonymous original-image read unexpectedly succeeded.")

    return {
        "status": "passed",
        "intake_id": intake["id"],
        "media_asset_id": intake["media_asset_id"],
        "controller": controller,
        "final_status": routed["status"],
        "audit_actions": sorted(actions),
        "authorized_original_sha256": routed["media_sha256"],
    }


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("IHOS_BASE_URL", "http://127.0.0.1:8081"))
    parser.add_argument("--email", default=os.getenv("BOOTSTRAP_ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.getenv("BOOTSTRAP_ADMIN_PASSWORD"))
    args = parser.parse_args()
    if not args.email or not args.password:
        raise SystemExit("BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD are required.")
    print(json.dumps(run(args.base_url, args.email, args.password), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
