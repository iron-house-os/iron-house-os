"""Staging-only command for issue #134 fuel-standard estimate revisions."""

import json
from argparse import ArgumentParser
from datetime import date
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.drive_tender_import import ImportValidationError
from app.services.fuel_estimate_staging_import import (
    expired_revision_keys,
    import_fuel_estimate_revisions,
)
from app.tools.drive_tender_import import _optional_lock, require_staging_apply

DEFAULT_LOCK_FILE = Path("/tmp/iron-house-os-fuel-estimate-staging-import.lock")


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Dry-run or apply issue #134 estimate revisions.")
    parser.add_argument("--operator", required=True, help="Named audit actor running the import.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply atomically to staging; default is dry-run.",
    )
    parser.add_argument(
        "--confirm-provisional-estimates",
        action="store_true",
        help="Acknowledge that estimator confirmation is still required before submission.",
    )
    parser.add_argument(
        "--confirm-expired-intake",
        action="store_true",
        help="Acknowledge any tender whose closing date has passed at apply time.",
    )
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK_FILE)
    return parser


def require_provisional_confirmation(apply: bool, confirmed: bool) -> None:
    if apply and not confirmed:
        raise ImportValidationError(
            "Applying provisional fuel estimates requires --confirm-provisional-estimates."
        )


def require_expired_intake_confirmation(apply: bool, confirmed: bool, as_of: date) -> None:
    expired = expired_revision_keys(as_of)
    if apply and expired and not confirmed:
        raise ImportValidationError(
            "Applying after tender closing requires --confirm-expired-intake for: "
            + ", ".join(expired)
        )


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    try:
        require_staging_apply(settings.environment, args.apply)
        require_provisional_confirmation(args.apply, args.confirm_provisional_estimates)
        require_expired_intake_confirmation(args.apply, args.confirm_expired_intake, date.today())
        with _optional_lock(args.apply, args.lock_file), SessionLocal() as db:
            report = import_fuel_estimate_revisions(db, actor=args.operator, apply=args.apply)
            if args.apply:
                db.commit()
            else:
                db.rollback()
    except (ImportValidationError, OSError) as exc:
        print(json.dumps({"status": "blocked", "issues": [str(exc)]}, indent=2))
        raise SystemExit(2) from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
