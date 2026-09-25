#!/usr/bin/env python3
"""Build a protected QuickBooks live read-only production environment candidate."""

from __future__ import annotations

import argparse
import secrets
from collections.abc import Callable
from pathlib import Path


PRODUCTION_REDIRECT_URI = (
    "https://os.ironhousecivil.com/api/v1/finance/quickbooks/oauth/callback"
)
PRODUCTION_RETURN_URI = "https://os.ironhousecivil.com/finance"


def _values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value
    return values


def render_environment(
    source: str,
    action: str,
    *,
    token_factory: Callable[[], str] | None = None,
) -> str:
    if action not in {"activate", "force-disable"}:
        raise ValueError("action must be activate or force-disable")

    lines = source.splitlines()
    values = _values(lines)
    updates = {
        "QUICKBOOKS_ENABLED": "false",
        "QUICKBOOKS_FORCE_DISABLED": "false" if action == "activate" else "true",
    }

    if action == "activate":
        if values.get("QUICKBOOKS_ENABLED", "false").strip().lower() not in {
            "",
            "false",
        }:
            raise ValueError(
                "QUICKBOOKS_ENABLED must remain false for database-managed credentials."
            )
        if values.get("QUICKBOOKS_CLIENT_ID", "").strip() or values.get(
            "QUICKBOOKS_CLIENT_SECRET", ""
        ).strip():
            raise ValueError(
                "Environment-based QuickBooks credentials must be empty; "
                "use the administrator UI."
            )

        existing_key = values.get("QUICKBOOKS_TOKEN_ENCRYPTION_KEY", "").strip()
        already_active = (
            values.get("QUICKBOOKS_ENVIRONMENT", "").strip().lower()
            == "production"
            and values.get("QUICKBOOKS_LIVE_READ_ONLY_APPROVED", "")
            .strip()
            .lower()
            == "true"
            and len(existing_key) >= 32
        )
        make_token = token_factory or (lambda: secrets.token_urlsafe(48))
        updates.update(
            {
                "QUICKBOOKS_ENVIRONMENT": "production",
                "QUICKBOOKS_LIVE_READ_ONLY_APPROVED": "true",
                "QUICKBOOKS_CLIENT_ID": "",
                "QUICKBOOKS_CLIENT_SECRET": "",
                "QUICKBOOKS_REDIRECT_URI": PRODUCTION_REDIRECT_URI,
                "QUICKBOOKS_FRONTEND_RETURN_URL": PRODUCTION_RETURN_URI,
                "QUICKBOOKS_TOKEN_ENCRYPTION_KEY": (
                    existing_key if already_active else make_token()
                ),
            }
        )

    rendered: list[str] = []
    written: set[str] = set()
    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            rendered.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            if key not in written:
                rendered.append(f"{key}={updates[key]}")
                written.add(key)
            continue
        rendered.append(line)

    for key, value in updates.items():
        if key not in written:
            rendered.append(f"{key}={value}")
    return "\n".join(rendered) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("activate", "force-disable"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()

    rendered = render_environment(args.source.read_text(), args.action)
    args.candidate.write_text(rendered)


if __name__ == "__main__":
    main()
