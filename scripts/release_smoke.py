#!/usr/bin/env python3
"""Smoke-test a deployed Iron House OS release using only the standard library."""

from argparse import ArgumentParser
from base64 import b64encode
from datetime import UTC, datetime
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def _authorization(username: str | None, password: str | None) -> str | None:
    if not username and not password:
        return None
    if not username or not password:
        raise SystemExit("Both username and password are required when authentication is enabled.")
    token = b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def _request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    body: bytes | None = None,
    content_type: str | None = None,
    authorization: str | None = None,
    expected: tuple[int, ...] = (200,),
) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    if payload is not None:
        body = json.dumps(payload).encode()
        content_type = "application/json"
    if content_type:
        headers["Content-Type"] = content_type
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            status_code = response.status
            response_body = response.read()
    except HTTPError as exc:
        response_body = exc.read()
        raise RuntimeError(
            f"{method} {path} returned {exc.code}: {response_body.decode(errors='replace')}"
        ) from exc
    if status_code not in expected:
        raise RuntimeError(f"{method} {path} returned {status_code}; expected {expected}")
    return status_code, response_body


def _json_request(*args, **kwargs) -> dict:
    _, body = _request(*args, **kwargs)
    return json.loads(body)


def _minimal_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, value in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(value)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)


def _multipart(fields: dict[str, str], filename: str, file_bytes: bytes) -> tuple[bytes, str]:
    boundary = f"ihos-{uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{filename}"\r\n'
            ).encode(),
            b"Content-Type: application/pdf\r\n\r\n",
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def run(base_url: str, authorization: str | None, full: bool) -> dict:
    _, homepage = _request(base_url, "/", authorization=authorization)
    if b"Iron House" not in homepage:
        raise RuntimeError("The frontend response did not contain the Iron House application shell.")
    readiness = _json_request(base_url, "/readiness", authorization=authorization)
    if readiness.get("status") != "ready":
        raise RuntimeError(f"Release is not ready: {readiness}")
    if not full:
        return {"mode": "read-only", "status": "passed"}

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    project = _json_request(
        base_url,
        "/api/v1/projects",
        method="POST",
        payload={
            "name": f"Build 207 release smoke {stamp}",
            "municipality": "Surrey",
            "project_number": f"SMOKE-{stamp}",
        },
        authorization=authorization,
        expected=(201,),
    )
    estimate = _json_request(
        base_url,
        "/api/v1/estimates/summary",
        method="POST",
        payload={
            "project_name": project["name"],
            "project_code": project["project_number"],
            "line_items": [
                {
                    "code": "SMOKE-001",
                    "description": "Release validation item",
                    "item_type": "material",
                    "quantity": 1,
                    "unit": "EA",
                    "labour": [],
                    "equipment": [],
                    "materials": [],
                    "disposal": [],
                    "vendor_quotes": [],
                    "direct_unit_cost": 1,
                }
            ],
            "indirects": [],
            "risks": [],
            "markup": {
                "overhead_percent": 0,
                "profit_percent": 0,
                "contingency_percent": 0,
                "bonding_percent": 0,
                "insurance_percent": 0,
            },
            "assumptions": ["Automated release validation only."],
            "exclusions": [],
        },
        authorization=authorization,
    )
    if estimate.get("final_price") != 1:
        raise RuntimeError(f"Unexpected estimate result: {estimate}")

    rfq = _json_request(
        base_url,
        "/api/v1/rfqs",
        method="POST",
        payload={
            "title": f"Build 207 release RFQ {stamp}",
            "project_id": project["id"],
            "project_name": project["name"],
            "scope_summary": "Automated release validation only.",
            "supplier_category_targets": [],
        },
        authorization=authorization,
        expected=(201,),
    )

    pdf = _minimal_pdf("Quantity Schedule: 12 m storm pipe. Field verify utility crossing.")
    multipart, content_type = _multipart(
        {
            "project_id": project["id"],
            "title": "Build 207 release drawing",
            "municipality": "Surrey",
        },
        "build-207-release.pdf",
        pdf,
    )
    drawing = _json_request(
        base_url,
        "/api/v1/drawing-intelligence/ingest",
        method="POST",
        body=multipart,
        content_type=content_type,
        authorization=authorization,
        expected=(201,),
    )
    if drawing["source"]["project_id"] != project["id"]:
        raise RuntimeError("Drawing upload was not linked to the release-smoke project.")

    return {
        "mode": "full",
        "status": "passed",
        "project_id": project["id"],
        "rfq_package_id": rfq["id"],
        "drawing_document_id": drawing["source"]["document_id"],
    }


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("IHOS_BASE_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--username", default=os.getenv("IHOS_ADMIN_USERNAME"))
    parser.add_argument("--password", default=os.getenv("IHOS_ADMIN_PASSWORD"))
    parser.add_argument("--full", action="store_true", help="Create release-smoke records and upload a PDF.")
    args = parser.parse_args()
    authorization = _authorization(args.username, args.password)
    print(json.dumps(run(args.base_url, authorization, args.full), indent=2))


if __name__ == "__main__":
    main()
