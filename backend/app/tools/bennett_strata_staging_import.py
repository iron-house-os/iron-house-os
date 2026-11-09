"""Staging-only command for issue #314 Bennett Strata estimate intake."""

import json
from argparse import ArgumentParser
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.bennett_strata_staging_import import import_bennett_strata_estimates
from app.services.drive_tender_import import ImportValidationError
from app.tools.drive_tender_import import _optional_lock, require_staging_apply

DEFAULT_LOCK_FILE = Path("/tmp/iron-house-os-bennett-strata-staging-import.lock")


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Dry-run or apply issue #314 Bennett Strata estimates.")
    parser.add_argument("--operator", required=True, help="Named audit actor running the import.")
    parser.add_argument("--apply", action="store_true", help="Apply atomically to staging; default is dry-run.")
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK_FILE)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    try:
        require_staging_apply(settings.environment, args.apply)
        with _optional_lock(args.apply, args.lock_file), SessionLocal() as db:
            report = import_bennett_strata_estimates(db, actor=args.operator, apply=args.apply)
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
