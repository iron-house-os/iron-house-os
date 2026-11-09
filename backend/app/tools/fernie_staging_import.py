"""Staging-only command for the historical Fernie 2026 bid package."""

import json
from argparse import ArgumentParser
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.drive_tender_import import ImportValidationError, load_manifest
from app.services.fernie_staging_import import import_fernie_bid_package
from app.tools.drive_tender_import import _optional_lock, require_staging_apply

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "data" / "drive_tenders_manifest.json"
DEFAULT_LOCK_FILE = Path("/tmp/iron-house-os-fernie-staging-import.lock")


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Dry-run or apply the historical Fernie staging intake.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--operator", required=True, help="Named audit actor running the import.")
    parser.add_argument("--apply", action="store_true", help="Apply atomically to staging; default is dry-run.")
    parser.add_argument(
        "--confirm-expired-intake",
        action="store_true",
        help="Acknowledge that the 2026-08-14 tender closing has passed.",
    )
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK_FILE)
    return parser


def require_expired_intake_confirmation(apply: bool, confirmed: bool) -> None:
    if apply and not confirmed:
        raise ImportValidationError(
            "Applying the historical Fernie intake requires --confirm-expired-intake."
        )


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    try:
        require_staging_apply(settings.environment, args.apply)
        require_expired_intake_confirmation(args.apply, args.confirm_expired_intake)
        folders = load_manifest(args.manifest)
        with _optional_lock(args.apply, args.lock_file), SessionLocal() as db:
            report = import_fernie_bid_package(
                db,
                folders,
                actor=args.operator,
                apply=args.apply,
            )
            if args.apply:
                db.commit()
            else:
                db.rollback()
    except (ImportValidationError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "issues": [str(exc)]}, indent=2))
        raise SystemExit(2) from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
