"""Staging-only admin command for the Google Drive tender metadata import."""

import fcntl
import json
import sys
from argparse import ArgumentParser
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.drive_tender_import import (
    ImportValidationError,
    import_drive_tenders,
    load_manifest,
)

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "data" / "drive_tenders_manifest.json"
DEFAULT_LOCK_FILE = Path("/tmp/iron-house-os-drive-tender-import.lock")


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Dry-run or apply the checked-in Drive tender manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--operator", required=True, help="Named audit actor running the import.")
    parser.add_argument("--apply", action="store_true", help="Apply atomically; default is dry-run.")
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK_FILE)
    return parser


def require_staging_apply(environment: str, apply: bool) -> None:
    if apply and environment.casefold() != "staging":
        raise ImportValidationError("Apply is locked to an IHOS staging environment.")


@contextmanager
def _exclusive_import_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ImportValidationError("Another Drive tender import is already running.") from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


@contextmanager
def _optional_lock(apply: bool, path: Path) -> Iterator[None]:
    if apply:
        with _exclusive_import_lock(path):
            yield
    else:
        yield


def _print_blocked(exc: Exception, output: TextIO) -> None:
    print(json.dumps({"status": "blocked", "issues": [str(exc)]}, indent=2), file=output)


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    try:
        require_staging_apply(settings.environment, args.apply)
        folders = load_manifest(args.manifest)
        with _optional_lock(args.apply, args.lock_file), SessionLocal() as db:
            report = import_drive_tenders(db, folders, actor=args.operator, apply=args.apply)
            if args.apply:
                db.commit()
            else:
                db.rollback()
    except (ImportValidationError, OSError, json.JSONDecodeError) as exc:
        _print_blocked(exc, output=sys.stdout)
        raise SystemExit(2) from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
